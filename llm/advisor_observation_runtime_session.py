"""Core-only session bundle and active-session authority for observation replay."""
from copy import deepcopy

from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_observation_replay_persistence_commands import ObservationReplayPersistenceCommands
from llm.advisor_observation_replay_runtime import ObservationReplayRuntime


class BattleObservationRuntimeSession:
    """One immutable-session bundle; it never resets or rebinds components."""

    def __init__(self, session_id, collection, runtime, commands):
        self._session_id = session_id
        self._collection = collection
        self._runtime = runtime
        self._commands = commands
        self._last_allocated_sequence = 0

    @classmethod
    def create(cls, session_id, initial_state):
        if not _valid_initial_input(session_id, initial_state):
            return _creation_result("invalid_initial_state")
        try:
            collection = ObservationCollection(session_id)
            runtime_result = ObservationReplayRuntime.create(deepcopy(initial_state))
            if runtime_result.get("status") != "ready":
                return _creation_result("invalid_initial_state")
            runtime = runtime_result["runtime"]
            commands_result = ObservationReplayPersistenceCommands.create(runtime)
            if commands_result.get("status") != "ready":
                return _creation_result("creation_failed")
            commands = commands_result["commands"]
            if not _matching_components(session_id, collection, runtime, commands):
                return _creation_result("creation_failed")
            return {"status": "session_ready", "session": cls(session_id, collection, runtime, commands), "session_id": session_id}
        except Exception:
            return _creation_result("creation_failed")

    @property
    def session_id(self): return self._session_id

    @property
    def last_allocated_sequence(self): return self._last_allocated_sequence

    def allocate_observation_sequence(self):
        self._last_allocated_sequence += 1
        return {"status": "allocated", "session_id": self._session_id, "observation_sequence": self._last_allocated_sequence}

    def read_collection_snapshot(self): return deepcopy(self._collection.snapshot(self._session_id))
    def read_state(self): return deepcopy(self._runtime.read_state())
    def capture_runtime_state_snapshot(self, captured_session_id):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        read = self._runtime.read_state()
        if read.get("status") != "ready" or read.get("session_id") != self._session_id:
            return _runtime_snapshot_result("invalid_runtime_state", self._session_id)
        return {
            "status": "runtime_snapshot_ready",
            "session_id": self._session_id,
            "state": deepcopy(read.get("state")),
            "state_fingerprint": read.get("state_fingerprint"),
        }
    def read_applied_ledger(self): return deepcopy(self._runtime.read_applied_ledger())

    def validate_session(self, captured_session_id):
        return _session_result("current_session" if captured_session_id == self._session_id else "stale_session", self._session_id)

    def admit_confirmation(self, captured_session_id, confirmation_result):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._collection.add_confirmation_result(deepcopy(confirmation_result)))

    def admit_confirmations_atomically(self, captured_session_id, confirmation_results):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._collection.add_confirmation_results(deepcopy(confirmation_results)))

    def preview(self, captured_session_id, observation_snapshot):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._runtime.preview(deepcopy(observation_snapshot)))

    def apply(self, captured_session_id, observation_snapshot):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._runtime.apply(deepcopy(observation_snapshot)))

    def save(self, captured_session_id, path):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._commands.save(path))

    def load(self, captured_session_id, path):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._commands.load(path))

    def restore(self, captured_session_id, candidate, expected_runtime_fingerprint):
        if captured_session_id != self._session_id: return _session_result("stale_session", self._session_id)
        return deepcopy(self._commands.restore(deepcopy(candidate), expected_runtime_fingerprint))


class BattleObservationRuntimeSessionManager:
    """Own exactly one active bundle; rollover publishes only a complete replacement."""

    def __init__(self, active_session): self._active_session = active_session

    @classmethod
    def create(cls, session_id, initial_state):
        created = BattleObservationRuntimeSession.create(session_id, initial_state)
        if created.get("status") != "session_ready":
            return {"status": created["status"], "manager": None, "session_id": None}
        manager = cls(created["session"])
        return {"status": "session_ready", "manager": manager, "session_id": manager.session_id}

    @property
    def session_id(self): return self._active_session.session_id
    @property
    def last_allocated_sequence(self): return self._active_session.last_allocated_sequence

    def rollover(self, session_id, initial_state):
        if isinstance(session_id, str) and session_id and session_id == self.session_id:
            return _session_result("session_unchanged", self.session_id)
        created = BattleObservationRuntimeSession.create(session_id, initial_state)
        if created.get("status") != "session_ready":
            return _session_result(created["status"], self.session_id)
        self._active_session = created["session"]
        return _session_result("session_replaced", self.session_id)

    def validate_active_session(self, captured_session_id): return self._active_session.validate_session(captured_session_id)
    def validate_worker_result_session(self, captured_session_id):
        return _session_result("current_session" if captured_session_id == self.session_id else "stale_worker_result", self.session_id)
    def allocate_observation_sequence(self): return deepcopy(self._active_session.allocate_observation_sequence())
    def read_collection_snapshot(self): return self._active_session.read_collection_snapshot()
    def read_state(self): return self._active_session.read_state()
    def capture_runtime_state_snapshot(self, captured_session_id): return self._active_session.capture_runtime_state_snapshot(captured_session_id)
    def read_applied_ledger(self): return self._active_session.read_applied_ledger()
    def admit_confirmation(self, captured_session_id, confirmation_result): return self._active_session.admit_confirmation(captured_session_id, confirmation_result)
    def admit_confirmations_atomically(self, captured_session_id, confirmation_results): return self._active_session.admit_confirmations_atomically(captured_session_id, confirmation_results)
    def preview(self, captured_session_id, observation_snapshot): return self._active_session.preview(captured_session_id, observation_snapshot)
    def apply(self, captured_session_id, observation_snapshot): return self._active_session.apply(captured_session_id, observation_snapshot)
    def save(self, captured_session_id, path): return self._active_session.save(captured_session_id, path)
    def load(self, captured_session_id, path): return self._active_session.load(captured_session_id, path)
    def restore(self, captured_session_id, candidate, expected_runtime_fingerprint): return self._active_session.restore(captured_session_id, candidate, expected_runtime_fingerprint)


def _valid_initial_input(session_id, initial_state):
    return isinstance(session_id, str) and bool(session_id) and isinstance(initial_state, dict) and initial_state.get("session_id") == session_id


def _matching_components(session_id, collection, runtime, commands):
    return collection.snapshot().get("session_id") == session_id and runtime.session_id == session_id and commands.session_id == session_id


def _creation_result(status): return {"status": status, "session": None, "session_id": None}
def _session_result(status, session_id): return {"status": status, "session_id": session_id}
def _runtime_snapshot_result(status, session_id): return {"status": status, "session_id": session_id, "state": None, "state_fingerprint": None}
