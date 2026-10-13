"""Gymnasium adapter around the validated local environment, no new mechanics."""

import gymnasium as gym
import numpy as np
from collections import Counter
from advisor.showdown_environment import ShowdownEnvironment
from advisor.learned_baselines import VisibleBaseline
from advisor.learned_scenarios import scenario
from advisor.learned_encoder import fingerprint
from copy import deepcopy


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
    ):
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
        self.tactical_counts = Counter()
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
        }
        self._rejected_choices = 0
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
        encoded = self.encoder.encode(self.current)
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
        if self.collect_tactical_metrics:
            from advisor.learned_tactical_diagnostics import action_class

            self.tactical_counts[action_class(self.current, int(action))] += 1
        result = self.native.step(
            {
                "self": int(action),
                "opponent": self.opponent.act(
                    self.native.observation("opponent", include_history=True)
                ),
            },
            revision=self.current["revision"],
        )
        self._rejected_choices += int(result["action_rejected"])
        self.current = self.native.observation("self", include_history=True)
        while (
            not (result["terminated"] or result["truncated"])
            and self.current["action_mask"][26]
        ):
            result = self.native.step(
                {
                    "self": 26,
                    "opponent": self.opponent.act(
                        self.native.observation("opponent", include_history=True)
                    ),
                },
                revision=self.current["revision"],
            )
            self.current = self.native.observation("self", include_history=True)
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
        return (
            self.encoder.encode(final_view),
            float(result["rewards"]["self"]),
            result["terminated"],
            result["truncated"],
            {
                **self._policy_info(),
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

    def pending_completed_count(self):
        return len(self.completed)

    def episode_cursor(self):
        """Coordinator audit inputs, not an exact mid-rollout restart checkpoint."""
        return {"episode_identity": deepcopy(self._episode_identity), "next_case_index": self.index,
                "revision": self.current["revision"], "request_state": self.current["request_state"],
                "scope": "initial_scenario_reconstructable_no_training_action_log_or_rollout_rng_restoration"}

    def close(self):
        self.native.close()
