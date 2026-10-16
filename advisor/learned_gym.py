"""Gymnasium adapter around the validated local environment, no new mechanics."""

import gymnasium as gym
import numpy as np
from collections import Counter
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario
from advisor.learned_encoder import fingerprint
from copy import deepcopy

OPAQUE_TERMINAL = "native-opaque-terminal-transport-v1"


class ShowdownLearningEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        checkout,
        encoder,
        *,
        split="train",
        index_offset=0,
        max_decisions=256,
        curriculum_version="showdown-learning-curriculum-v1",
        opponents=None,
        opponent_factory=None,
        collect_tactical_metrics=False,
        diagnostic_directory=None,
        collect_public_trajectories=False,
        terminal_transport_version=None,
        training_subset=None,
        collect_v5_supervision=False,
    ):
        if collect_public_trajectories and not collect_tactical_metrics:
            raise ValueError("public_collection_requires_public_execution_metrics")
        if terminal_transport_version not in (None, OPAQUE_TERMINAL):
            raise ValueError("unsupported_native_terminal_transport")
        if training_subset is not None and curriculum_version != "showdown-learning-curriculum-v8":
            raise ValueError("training_subset_requires_native_v8")
        self.native = ShowdownEnvironment(checkout, max_decisions=max_decisions)
        self.encoder, self.split, self.index, self.offset = (
            encoder,
            split,
            0,
            index_offset,
        )
        self.action_space = gym.spaces.Discrete(35)
        self.observation_space = None
        self.completed = []
        self.current = None
        self.curriculum_version = curriculum_version
        self.opponents = opponents or ("random", "max_power", "heuristic")
        self.opponent_factory = opponent_factory
        self._behavior_cache = {}
        self.coverage_counts = {}
        self.collect_tactical_metrics = collect_tactical_metrics
        self.diagnostic_directory = diagnostic_directory
        self.collect_public_trajectories = collect_public_trajectories
        self._collection_step = None
        self.terminal_transport_version = terminal_transport_version
        self.training_subset = training_subset
        self.collect_v5_supervision = collect_v5_supervision
        if collect_v5_supervision and encoder.version not in ("showdown-public-categorical-observation-v5-integrated-v1", "showdown-public-categorical-observation-v5-integrated-v2", "showdown-public-categorical-observation-v5-integrated-v3"):
            raise ValueError("v5_supervision_requires_v5_public_encoder")
        self.tactical_counts = Counter()
        self.retry_diagnostics = []
        self.public_behavior_counts = Counter()
        try:
            self.reset()
        except BaseException:
            self.native.close()
            raise

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.index = seed * 1000 + self.offset
        index = self.index
        self.index += 1
        current = (
            self.training_subset(self.split, index) if self.training_subset is not None else
            scenario(self.split, index, version=self.curriculum_version)
            if self.curriculum_version != "showdown-learning-curriculum-v1"
            else scenario(self.split, index)
        )
        from advisor.learned_tactical_curriculum import reset_learning_episode

        self.start_info = reset_learning_episode(self.native, current)
        # Coordinator provenance only; neither policy features nor Gym info.
        self._episode_identity = {
            "schema_version": "showdown-learning-episode-identity-v1",
            "curriculum_version": self.curriculum_version, "split": self.split,
            "case_index": index, "scenario_id": current["scenario_id"],
            "scenario_sha256": fingerprint(current),
            "team_sha256": {side: fingerprint(team) for side, team in current["teams"].items()},
            "preview": deepcopy(current["preview"]), "native_seed": list(current["seed"]),
            **({"training_subset_sha256": self.training_subset.identity["sha256"],
                "preview_protocol": self.training_subset.contract["selection_mode"]}
               if self.training_subset is not None else {}),
        }
        self._rejected_choices = 0
        from advisor.learned_public_metrics import PublicDecisionMetrics
        self._public_metrics = {side: PublicDecisionMetrics() for side in ("self", "opponent")}
        if self.curriculum_version in {
            "showdown-learning-curriculum-v7",
            "showdown-learning-curriculum-v8",
        }:
            # Privileged coordinator telemetry only. Never placed in observation,
            # info, reward, actor/critic features or labels.
            for side, team in current["teams"].items():
                selected = current["preview"][side]
                for scope, sets in (
                    ("roster", team),
                    ("brought", [team[i - 1] for i in selected]),
                ):
                    for p in sets:
                        for field, values in (
                            ("species", [p["species"]]),
                            ("moves", p["moves"]),
                            ("abilities", [p["ability"]]),
                            ("items", [p["item"] or "known_absence"]),
                        ):
                            self.coverage_counts.setdefault(
                                f"{side}_{scope}_{field}", Counter()
                            ).update(values)
        kind = (options or {}).get(
            "opponent", self.opponents[index % len(self.opponents)]
        )
        self.opponent = (
            self.opponent_factory(kind, index + 91)
            if self.opponent_factory
            else VisibleBaseline(kind, index + 91)
        )
        self.opponent_kind = kind
        self._episode_identity.update(opponent=kind, opponent_model_id=getattr(self.opponent, "model_id", None))
        self.current = self.native.observation("self", include_history=True)
        encoded = self._encode_public(self.current)
        if self.observation_space is None:
            self.observation_space = gym.spaces.Box(
                -2, 4, shape=encoded.shape, dtype=np.float32
            )
        return encoded, self._policy_info()

    def _policy_info(self):
        return {
            "schema_version": "showdown-learning-info-v2",
            "episode_id": self.current["episode_id"],
            "revision": self.current["revision"],
            "request_state": self.current["request_state"],
        }

    def action_masks(self):
        return np.asarray(self.current["action_mask"], dtype=bool)

    def behavior_action(self, kind, stochastic=False):
        """Offline collection helper: the actor receives only its own partial view."""
        if kind not in self._behavior_cache:
            self._behavior_cache[kind] = (
                self.opponent_factory(kind, self.index + 47)
                if self.opponent_factory
                else VisibleBaseline(kind, self.index + 47)
            )
        actor = self._behavior_cache[kind]
        if stochastic and hasattr(actor, "infer"):
            probabilities = np.asarray(
                actor.infer(self.current)["action_probabilities"]
            )
            action = int(
                self.np_random.choice(35, p=probabilities / probabilities.sum())
            )
        else:
            action = actor.act(self.current)
        if not self.action_masks()[action]:
            raise ValueError("masked_public_behavior_action")
        return action

    def behavior_decision(self, kind, stochastic=False):
        from advisor.learned_tactical_diagnostics import action_class

        action = self.behavior_action(kind, stochastic)
        return {"action": action, "category": action_class(self.current, action)}

    def step(self, action):
        if (
            not isinstance(action, (int, np.integer))
            or not 0 <= int(action) < 35
            or not self.action_masks()[int(action)]
        ):
            raise ValueError("masked_learning_action")
        if self.collect_v5_supervision:
            # Loss-only predecision supervision. Never installed in self.current,
            # encoder input, native rewards, actor observations or value targets.
            v5_before = deepcopy(self.current)
            v5_opponent = self.native.observation("opponent", include_history=True)
        if getattr(self, "collect_public_trajectories", False):
            from advisor.learned_failure_opponent import request_move
            collection_previous_features = self.encoder.encode(self.current)
            before_counts = Counter(self.public_behavior_counts)
            before_rejections = self._rejected_choices
            before_history = len(self.current["public_history"])
            selected_move = request_move(self.current, int(action))
        if self.collect_tactical_metrics:
            from advisor.learned_tactical_diagnostics import action_class

            self.tactical_counts[action_class(self.current, int(action))] += 1
        result = self._native_step(int(action))
        self.current = self.native.observation("self", include_history=True)
        while (
            not (result["terminated"] or result["truncated"])
            and self.current["action_mask"][26]
        ):
            result = self._native_step(26)
            self.current = self.native.observation("self", include_history=True)
        if getattr(self, "collect_public_trajectories", False):
            from advisor.learned_encoder import identifier
            events = self.current["public_history"][before_history:]
            self._collection_step = {
                "schema_version": "showdown-owner-public-execution-diagnostics-v1",
                "action": int(action), "selected_public_move": selected_move,
                "native_rejections": self._rejected_choices - before_rejections,
                "counts": {k.removeprefix("self:"): v - before_counts[k]
                           for k, v in self.public_behavior_counts.items() if k.startswith("self:")},
                "executed_public_moves": [identifier(p[3]) for line in events
                    for p in [line.split("|")] if len(p) > 3 and p[1] == "move" and p[2].startswith("p1")],
            }
        if result["terminated"] or result["truncated"]:
            self.completed.append(
                {
                    "winner": result["winner"],
                    "truncated": result["truncated"],
                    "decisions": result["decisions"],
                    "opponent": self.opponent_kind,
                    "terminated": result["terminated"],
                    "native_rejected_choices": self._rejected_choices,
                    "episode_identity": deepcopy(self._episode_identity),
                }
            )
        # SB3 records this tensor as terminal_observation and bootstraps only
        # TimeLimit.truncated. The real execution view remains closed/immutable.
        final_view = (self.native.timeout_bootstrap_observation("self")
                      if result["truncated"] else self.current)
        terminal_encoding_unavailable = False
        try:
            if result["terminated"] and getattr(self, "terminal_transport_version", None) == OPAQUE_TERMINAL:
                # Native terminal has no future policy decision/value bootstrap.
                # VecEnv replaces this administrative array with reset features.
                # Do not fabricate an encoded/public identity for the ended state.
                final_features = np.zeros(self.encoder.dimension, dtype=np.float32)
            else:
                final_features = self._encode_public(final_view)
        except ValueError:
            if not (getattr(self, "collect_public_trajectories", False) and result["terminated"]):
                raise
            # Collector-only administrative terminal transport. VecEnv resets
            # before the next actor call; the collector excludes this entire
            # episode. No placeholder is a data row, value target or bootstrap.
            final_features = collection_previous_features
            terminal_encoding_unavailable = True
        if getattr(self, "collect_public_trajectories", False):
            self._collection_step["terminal_encoding_unavailable"] = terminal_encoding_unavailable
        v5_targets = None
        if self.collect_v5_supervision:
            from advisor.learned_combat_v5_aux import supervision_targets
            if self.encoder.version == "showdown-public-categorical-observation-v5-integrated-v3":
                from advisor.learned_combat_v5_strategic_aux import supervision_targets
            v5_targets = supervision_targets(v5_before, v5_opponent,
                self.current["public_history"][len(v5_before["public_history"]):], self.encoder)
        return (
            final_features,
            float(result["rewards"]["self"]),
            result["terminated"],
            result["truncated"],
            {
                **self._policy_info(),
                **({"coordinator_v5_supervision": v5_targets} if self.collect_v5_supervision else {}),
                **({"collector_terminal_encoding_unavailable": True} if terminal_encoding_unavailable else {}),
                **({"terminal_transport_version": OPAQUE_TERMINAL}
                   if result["terminated"] and getattr(self, "terminal_transport_version", None) == OPAQUE_TERMINAL else {}),
                "native_outcome": {
                    k: result[k]
                    for k in (
                        "revision",
                        "decisions",
                        "terminated",
                        "truncated",
                        "winner",
                        "action_rejected",
                        "rewards",
                    )
                },
            },
        )

    def _encode_public(self, view):
        try:
            return self.encoder.encode(view)
        except ValueError as error:
            if getattr(self, "diagnostic_directory", None):
                from pathlib import Path
                from advisor.learning_resources import atomic_json
                directory = Path(self.diagnostic_directory)
                directory.mkdir(parents=True, exist_ok=True)
                atomic_json(directory / f"public_encoding_failure_{view['episode_id']}_{view['revision']}.json", {
                    "scope": "coordinator_only_actual_player_visible_view_no_checkpoint_hidden_sets_or_rng",
                    "encoder_version": self.encoder.version, "error": str(error),
                    "case_index": self._episode_identity["case_index"], "public_observation": view,
                })
            raise

    def collection_step_diagnostics(self):
        """Coordinator-only owner-visible evidence; survives VecEnv auto-reset.

        Never Gym info, policy/value features, opponent private view or RNG.
        """
        if not self.collect_public_trajectories or self._collection_step is None:
            raise ValueError("public_collection_diagnostics_not_enabled")
        return deepcopy(self._collection_step)

    def _native_step(self, action):
        other = self.native.observation("opponent", include_history=True)
        views = {"self": self.current, "opponent": other}
        actions = {"self": action, "opponent": self.opponent.act(other)}
        if self.collect_tactical_metrics:
            for side, view in views.items():
                self._public_metrics[side].decision(view, actions[side])
        result = self.native.step(actions, revision=self.current["revision"])
        self._rejected_choices += int(result["action_rejected"])
        if result["action_rejected"]:
            def flags(view, index):
                active = view["own_request"].get("active", [{}])[0]
                return {"choice": view["choices"][index], "action_index": index,
                        "action_mask": list(view["action_mask"]), "phase": view["request_state"],
                        "wait": bool(view["own_request"].get("wait")),
                        "trapped": active.get("trapped"), "maybeTrapped": active.get("maybeTrapped"),
                        "maybeDisabled": active.get("maybeDisabled")}
            self.retry_diagnostics.append({"episode_id": self.current["episode_id"],
                "episode_case": self._episode_identity["case_index"], "revision_before": self.current["revision"],
                "revision_after": result["revision"], "native_decisions": result["decisions"],
                "before": {s: flags(v, actions[s]) for s, v in views.items()},
                "after": {s: flags(self.native.observation(s), actions[s]) for s in views},
                "error_reason": "not_exposed_by_native_service_no_hidden_cause_inferred"})
        if self.collect_tactical_metrics:
            for side, view in views.items():
                after = self.native.observation(side, include_history=True)
                self._public_metrics[side].outcome(view, after["public_history"][len(view["public_history"]):])
                for name, count in self._public_metrics[side].drain_counts().items():
                    self.public_behavior_counts[f"{side}:{name}"] += count
            if hasattr(self.opponent, "drain_counts"):
                for name, count in self.opponent.drain_counts().items():
                    self.public_behavior_counts[f"opponent_policy:{name}"] += count
        return result

    def drain_completed(self):
        rows, self.completed = self.completed, []
        return rows

    def drain_coverage(self):
        result = {key: dict(value) for key, value in self.coverage_counts.items()}
        self.coverage_counts.clear()
        return result

    def learning_resources(self):
        return dict(self.native.resources)

    def drain_tactical_counts(self):
        result = dict(self.tactical_counts)
        self.tactical_counts.clear()
        return result

    def drain_public_behavior_counts(self):
        result = dict(self.public_behavior_counts)
        self.public_behavior_counts.clear()
        return result

    def drain_retry_diagnostics(self):
        rows, self.retry_diagnostics = self.retry_diagnostics, []
        return rows

    def pending_completed_count(self):
        return len(self.completed)

    def episode_cursor(self):
        """Coordinator audit inputs, not an exact mid-rollout restart checkpoint."""
        return {"episode_identity": deepcopy(self._episode_identity), "next_case_index": self.index,
                "revision": self.current["revision"], "request_state": self.current["request_state"],
                "native_rejected_choices": self._rejected_choices,
                "scope": "initial_scenario_reconstructable_no_training_action_log_or_rollout_rng_restoration"}

    def close(self):
        self.native.close()
