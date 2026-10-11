"""Bounded offline two-player environment using the existing pinned worker.

Trusted coordinators own this object. Policies receive observation(side) only.
No neural framework, socket, provider, live reducer write or ranking change.
"""
from __future__ import annotations
from contextlib import ExitStack
from copy import deepcopy
from threading import RLock
from uuid import uuid4

from advisor.showdown_bridge import FORMAT_ID, ShowdownBridgeError
from advisor.showdown_observation import project_policy_observation
from advisor.showdown_worker import ShowdownWorker

SCHEMA = "showdown-environment-v1"
SIDES = ("self", "opponent")


class ShowdownEnvironmentError(ShowdownBridgeError):
    pass


class ShowdownEnvironment:
    def __init__(self, checkout=None, *, worker=None, max_decisions=512):
        if worker is None and checkout is None:
            raise ValueError("explicit_showdown_checkout_required")
        self.worker = worker if worker is not None else ShowdownWorker(checkout)
        self._owns_worker = worker is None
        self.max_decisions = max_decisions
        self._lock = RLock()
        self._owner = None
        self._revision = None
        self._worker_generation = None
        self._history = {side: [] for side in SIDES}
        self._observations = {}
        self._transition = None
        self.resources = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _request(self, requests):
        try:
            result = self.worker.run({"schema_version": SCHEMA, "format_id": FORMAT_ID, "requests": requests})
        except ShowdownBridgeError:
            self._observations = {}
            self._transition = None
            self.resources = None
            raise
        self.resources = deepcopy(result["resources"])
        return result["results"]

    @staticmethod
    def _check(row):
        if row["status"] == "rejected":
            raise ShowdownEnvironmentError(row["reason"])
        return row

    def _install(self, row):
        if row["status"] == "rejected":
            if row.get("reason", "").endswith("restore_saved_checkpoint") or row.get("reason") == "native_environment_failed":
                self._close_episode()
                self._transition = None
            self._check(row)
        try:
            return self._project_transition(row)
        except (ShowdownBridgeError, KeyError, TypeError, ValueError, AttributeError) as error:
            # Native execution may already have advanced. Discard the handle;
            # never return cached pre-action observations as a fresh transition.
            self._revision = row.get("revision")
            self._worker_generation = self.worker.generation
            self._close_episode()
            self._transition = None
            raise ShowdownEnvironmentError("invalid_environment_transition_restore_saved_checkpoint") from error

    def _project_transition(self, row):
        if row["status"] != "ready" or set(row["observations"]) != set(SIDES):
            raise ShowdownEnvironmentError("invalid_environment_transition")
        rewards = row["rewards"]
        if (type(row["terminated"]) is not bool or type(row["truncated"]) is not bool or
            row["terminated"] and row["truncated"] or row["winner"] not in (*SIDES, None) or set(rewards) != set(SIDES) or
            any(type(v) is not int or v not in (-1, 0, 1) for v in rewards.values()) or
            rewards["self"] != -rewards["opponent"] or
            rewards["self"] != (1 if row["terminated"] and row["winner"] == "self" else
                                -1 if row["terminated"] and row["winner"] == "opponent" else 0)):
            raise ShowdownEnvironmentError("invalid_environment_reward")
        histories, observations = deepcopy(self._history), {}
        for side in SIDES:
            native = row["observations"][side]
            allowed_keys = {"schema_version", "episode_id", "revision", "side", "turn", "request_state", "terminated", "truncated",
                            "events", "own_request", "visible_active_health", "action_schema_version", "action_mask", "choices"}
            if (set(native) != allowed_keys or native.get("side") != side or native.get("episode_id") != self._owner or
                native.get("revision") != row["revision"] or native.get("action_schema_version") != "showdown-policy-actions-v1" or
                len(native.get("action_mask", [])) != 35 or len(native.get("choices", [])) != 35 or
                any(type(mask) is not int or mask not in (0, 1) or mask != int(choice is not None) or
                    (choice is not None and not isinstance(choice, str))
                    for mask, choice in zip(native["action_mask"], native["choices"]))):
                raise ShowdownEnvironmentError("invalid_environment_observation_binding")
            role = "p1" if side == "self" else "p2"
            request_side = native["own_request"].get("side")
            if request_side is not None and request_side.get("id") != role:
                raise ShowdownEnvironmentError("wrong_private_request_owner")
            histories[side].extend(native["events"])
            observations[side] = project_policy_observation(native, histories[side])
        self._history, self._observations = histories, observations
        self._revision = row["revision"]
        self._worker_generation = self.worker.generation
        self._transition = {key: deepcopy(row[key]) for key in ("revision", "decisions", "terminated", "truncated", "winner", "action_rejected", "rewards")}
        return deepcopy(self._transition)

    def _initialize(self, operation, **payload):
        with self._lock:
            self._close_episode()
            self._owner = uuid4().hex
            self._history = {side: [] for side in SIDES}
            self._observations = {}
            self._transition = None
            try:
                row = self._request([{"operation": operation, "owner": self._owner, "max_decisions": self.max_decisions, **payload}])[0]
                return self._install(row)
            except ShowdownBridgeError:
                self._owner = None
                raise

    def reset(self, scenario, *, seed=None):
        scenario = deepcopy(scenario)
        if seed is not None:
            scenario["seed"] = list(seed)
        return self._initialize("reset", scenario=scenario)

    def from_native_checkpoint(self, checkpoint):
        """Import through the existing detached compatibility authority first."""
        from llm.advisor_showdown_simulation import _checkpoint_fingerprint
        saved = deepcopy(checkpoint)
        fingerprint = saved.pop("checkpoint_fingerprint", None)
        if fingerprint != _checkpoint_fingerprint(saved):
            raise ShowdownEnvironmentError("detached_checkpoint_integrity_mismatch")
        return self._initialize("import_native", checkpoint=deepcopy(checkpoint))

    def restart(self, checkpoint):
        return self._initialize("restart", checkpoint=deepcopy(checkpoint))

    def observation(self, side, *, include_history=False):
        if side not in SIDES:
            raise ValueError("invalid_policy_side")
        with self._lock:
            if self._worker_generation != self.worker.generation or not self.worker.is_alive:
                raise ShowdownEnvironmentError("episode_process_lost_restore_saved_checkpoint")
            if side not in self._observations:
                raise ShowdownEnvironmentError("episode_not_initialized")
            return deepcopy({key: value for key, value in self._observations[side].items()
                             if include_history or key != "public_history"})

    def step(self, actions, *, revision):
        with self._lock:
            if self._owner is None:
                raise ShowdownEnvironmentError("episode_not_initialized")
            return self._install(self._request([{"operation": "step", "owner": self._owner,
                                                "revision": revision, "actions": deepcopy(actions)}])[0])

    @classmethod
    def batch_step(cls, entries):
        """One RPC for independent episodes on one explicitly shared worker."""
        if not entries or len(entries) > 64 or len({id(env) for env, _, _ in entries}) != len(entries):
            raise ValueError("invalid_environment_batch")
        worker = entries[0][0].worker
        if any(env.worker is not worker for env, _, _ in entries):
            raise ValueError("batch_requires_shared_worker")
        with ExitStack() as stack:
            for env in sorted((e[0] for e in entries), key=id):
                stack.enter_context(env._lock)
            requests = [{"operation": "step", "owner": env._owner, "revision": revision, "actions": deepcopy(actions)}
                        for env, actions, revision in entries]
            rows = entries[0][0]._request(requests)
            # Process every independent row, including successes after a rejection.
            results = []
            for (env, _, _), row in zip(entries, rows):
                try:
                    results.append(env._install(row))
                except ShowdownBridgeError as error:
                    results.append(error)
            return results

    def save(self):
        with self._lock:
            if self._owner is None:
                raise ShowdownEnvironmentError("episode_not_initialized")
            row = self._check(self._request([{"operation": "save", "owner": self._owner, "revision": self._revision}])[0])
            return deepcopy(row["checkpoint"])

    def fork(self):
        fork = type(self)(worker=self.worker, max_decisions=self.max_decisions)
        try:
            fork.restart(self.save())
        except BaseException:
            fork.close()
            raise
        return fork

    def _close_episode(self):
        if self._owner is not None:
            try:
                if self._worker_generation == self.worker.generation and self.worker.is_alive:
                    row = self._request([{"operation": "close", "owner": self._owner, "revision": self._revision}])[0]
                    if row.get("status") == "rejected" and row.get("reason") != "episode_not_found_restore_saved_checkpoint":
                        self._check(row)
            except ShowdownBridgeError:
                # Process loss already destroyed all native handles; never retry steps.
                pass
            self._owner = None
        self._observations = {}

    def close(self):
        with self._lock:
            self._close_episode()
            if self._owns_worker:
                self.worker.close()
