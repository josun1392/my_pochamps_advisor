"""Opt-in coordinator records; never an observation, reward, or optimizer owner.

The caller prepares BEFORE actor.forward, binds after the native step, and joins
only AFTER maintained SB3 GAE. Native payloads must stay outside Git worktrees.
"""
from copy import deepcopy
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np

from advisor.learned_action_signals import public_identity

VERSION = "showdown-decision-snapshot-GAE-join-v1"
FROZEN_GAE_SCOPE = "new_frozen_policy_rollout_not_historical_training_or_optimal_action_label"
PPO_GAE_SCOPE = "new_standard_PPO_rollout_not_counterfactual_or_historical_label"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def write_new(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        # Legacy numeric features traverse public mappings in insertion order.
        # Canonical hashes may sort keys; replay transport MUST NOT reorder them.
        json.dump(value, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())


def outside_git(directory):
    path = Path(directory).resolve()
    if any((p / ".git").exists() for p in (path, *path.parents)):
        raise ValueError("privileged_snapshots_require_non_git_directory")
    return path


def transition_identity(result):
    # Transport revision is assigned again at restart, not native game state.
    return {k: result[k] for k in ("decisions", "terminated", "truncated",
                                  "winner", "action_rejected", "rewards")}


class DecisionSnapshotRecorder:
    def __init__(self, directory, *, policy_id, every=64, max_snapshots=16,
                 max_checkpoint_bytes=32 * 1024 * 1024, gae_scope=FROZEN_GAE_SCOPE):
        if (type(every) is not int or every < 1 or type(max_snapshots) is not int
                or not 1 <= max_snapshots <= 32 or not 1024 <= max_checkpoint_bytes <= 32 * 1024 * 1024
                or len(policy_id) != 64 or any(c not in "0123456789abcdef" for c in policy_id)):
            raise ValueError("bounded_snapshot_contract_required")
        if gae_scope not in (FROZEN_GAE_SCOPE, PPO_GAE_SCOPE):
            raise ValueError("explicit_snapshot_GAE_scope_required")
        self.gae_scope = gae_scope
        self.directory = outside_git(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        for name in ("private", "public", "joins"):
            (self.directory / name).mkdir()
        self.policy_id, self.every, self.maximum = policy_id, every, max_snapshots
        self.byte_cap, self.bytes = max_checkpoint_bytes, 0
        self.roots, self.blocks, self.prepared = [], set(), None
        self.pending_native = None
        self.seconds = 0.

    def prepare(self, env, *, step, rollout, t):
        """Called by coordinator before forward, never from a policy or mask query."""
        if env.split != "train" or self.prepared is not None:
            raise ValueError("snapshot_prepare_boundary_mismatch")
        view = env.current
        block = step // self.every
        if (len(self.roots) >= self.maximum or block in self.blocks
                or view["request_state"] != "move" or sum(view["action_mask"]) < 2):
            return
        start = perf_counter()
        cp = env.native.save()
        root_id = digest([VERSION, self.policy_id, rollout, t, step,
                          view["episode_id"], view["revision"]])
        public = deepcopy(view)
        features = env.encoder.encode(public)
        root = {"id": root_id, "step": step, "rollout": rollout, "t": t,
                "policy_id": self.policy_id, "episode_id": view["episode_id"],
                "revision": view["revision"], "turn": view["turn"],
                "public_identity": public_identity(public),
                "observation_sha256": sha256(features.tobytes()).hexdigest(),
                "action_mask": list(view["action_mask"]), "checkpoint_digest": cp["digest"],
                "native_decisions": cp["decisions"], "trace": [], "joined": False,
                "native_terminal_recorded": False}
        raw = gzip.compress(json.dumps(cp, allow_nan=False).encode(), mtime=0)
        if self.bytes + len(raw) > self.byte_cap:
            raise ValueError("snapshot_storage_cap")
        path = self.directory / "private" / (root_id + ".json.gz")
        with path.open("xb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        self.bytes += len(raw)
        root["checkpoint_file_sha256"] = sha256(raw).hexdigest()
        write_new(self.directory / "public" / (root_id + ".json"), {
            "schema_version": VERSION, "id": root_id, "policy_id": self.policy_id,
            "scope": "owner_public_before_actor_forward", "observation": public,
            "observation_sha256": root["observation_sha256"]})
        self.roots.append(root); self.blocks.add(block); self.prepared = root
        self.seconds += perf_counter() - start

    def native_before(self, native, views, actions):
        targets = [r for r in self.roots if r["episode_id"] == views["self"]["episode_id"]
                   and not r["native_terminal_recorded"]]
        if not targets:
            return
        if self.pending_native is not None or any(not views[s]["action_mask"][a] for s, a in actions.items()):
            raise ValueError("snapshot_native_action_boundary")
        for root in targets:
            if not root["trace"] and (public_identity(views["self"]) != root["public_identity"]
                                      or native.save()["digest"] != root["checkpoint_digest"]):
                raise ValueError("snapshot_changed_between_prepare_and_native_action")
        self.pending_native = (targets, {"actions": {s: int(a) for s, a in actions.items()},
            "before_public": {s: public_identity(v) for s, v in views.items()}})

    def native_after(self, native, result):
        if self.pending_native is None:
            return
        start = perf_counter()
        targets, row = self.pending_native
        cp = native.save()
        row.update(native_digest_after=cp["digest"], result=transition_identity(result),
                   after_public={s: public_identity(native.observation(s, include_history=True))
                                 for s in ("self", "opponent")})
        for root in targets:
            line = json.dumps(row, allow_nan=False) + "\n"
            self.bytes += len(line.encode())
            if self.bytes > self.byte_cap:
                raise ValueError("snapshot_storage_cap")
            root["trace"].append(deepcopy(row))
            root["native_terminal_recorded"] = bool(result["terminated"] or result["truncated"])
            with (self.directory / "private" / (root["id"] + ".trace.jsonl")).open("a", encoding="utf-8") as f:
                f.write(line); f.flush(); os.fsync(f.fileno())
        self.pending_native = None
        self.seconds += perf_counter() - start

    def selected(self, *, action, value, logp, features, mask):
        if self.prepared is None:
            return
        root = self.prepared
        if (not root["trace"] or root["trace"][0]["actions"]["self"] != int(action)
                or sha256(features.tobytes()).hexdigest() != root["observation_sha256"]
                or list(map(int, mask)) != root["action_mask"] or not mask[int(action)]
                or not np.isfinite([value, logp]).all()):
            raise ValueError("snapshot_selected_action_join_mismatch")
        root.update(action=int(action), value=float(value), old_logp=float(logp))
        self.prepared = None

    def join(self, buffer, rollout):
        for root in self.roots:
            if root["rollout"] != rollout or root["joined"]:
                continue
            t = root["t"]
            if ("action" not in root or int(buffer.actions[t, 0, 0]) != root["action"]
                    or float(buffer.values[t, 0]) != root["value"]
                    or float(buffer.log_probs[t, 0]) != root["old_logp"]
                    or sha256(buffer.observations[t, 0].tobytes()).hexdigest() != root["observation_sha256"]
                    or list(map(int, buffer.action_masks[t, 0])) != root["action_mask"]):
                raise ValueError("snapshot_GAE_join_mismatch")
            root.update(advantage=float(buffer.advantages[t, 0]),
                        return_target=float(buffer.returns[t, 0]),
                        reward=float(buffer.rewards[t, 0]),
                        episode_start=bool(buffer.episode_starts[t, 0]), joined=True)
            if not np.isfinite([root["advantage"], root["return_target"]]).all():
                raise ValueError("nonfinite_snapshot_GAE")
            write_new(self.directory / "joins" / (root["id"] + ".json"), {
                **{k: v for k, v in root.items() if k != "trace"}, "schema_version": VERSION,
                "GAE_scope": self.gae_scope})

    def finish(self):
        if self.pending_native is not None or self.prepared is not None or any(not r["joined"] for r in self.roots):
            raise ValueError("unsettled_snapshot_capture")
        write_new(self.directory / "capture_manifest.json", {
            "schema_version": VERSION, "roots": [{k: v for k, v in r.items() if k != "trace"} for r in self.roots],
            "checkpoint_bytes": self.bytes, "instrumentation_seconds": self.seconds,
            "scope": "private_native_replay_only_never_policy_features"})


def read_root(directory, root):
    directory = Path(directory)
    raw = (directory / "private" / (root["id"] + ".json.gz")).read_bytes()
    if sha256(raw).hexdigest() != root["checkpoint_file_sha256"] or not root["joined"]:
        raise ValueError("snapshot_integrity_or_GAE_missing")
    cp = json.loads(gzip.decompress(raw))
    if cp["digest"] != root["checkpoint_digest"]:
        raise ValueError("snapshot_checkpoint_identity")
    return cp


def replay_original(native, checkpoint, root, public, *, stopping=None):
    """Full recorded native suffix, including wait/retries and original PRNG."""
    if not root["joined"] or not root["native_terminal_recorded"] or not root["trace"]:
        raise ValueError("complete_native_suffix_and_GAE_required")
    native.restart(checkpoint)
    if native.save() != checkpoint or public_identity(native.observation("self", include_history=True)) != public_identity(public):
        raise ValueError("snapshot_root_replay_mismatch")
    for row in root["trace"]:
        if stopping and stopping():
            raise TimeoutError("snapshot_replay_stop")
        views = {s: native.observation(s, include_history=True) for s in ("self", "opponent")}
        if {s: public_identity(v) for s, v in views.items()} != row["before_public"]:
            raise ValueError("snapshot_predecision_replay_mismatch")
        result = native.step(row["actions"], revision=views["self"]["revision"])
        if (transition_identity(result) != row["result"] or native.save()["digest"] != row["native_digest_after"]
                or {s: public_identity(native.observation(s, include_history=True)) for s in views} != row["after_public"]):
            raise ValueError("snapshot_native_suffix_replay_mismatch")
    return {"matched_native_steps": len(root["trace"]), "terminal": row["result"],
            "final_native_digest": row["native_digest_after"]}
