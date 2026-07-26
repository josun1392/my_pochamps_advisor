"""Runtime-neutral, process-local ownership for committed battle-state-v1."""
from copy import deepcopy
from threading import RLock

from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, state_fingerprint, validate_battle_state_unknown_markers


class BattleStateStore:
    """Single-current-session owner with detached snapshots and CAS replacement.

    The lock protects only copy/fingerprint/assignment. Callers perform planning
    and execution outside it, then supply the fingerprint observed on read.
    """
    def __init__(self, initial_state=None):
        self._lock = RLock()
        self._state = deepcopy(initial_state) if _valid_state(initial_state) else None

    def read_snapshot(self, session_id=None):
        with self._lock:
            if self._state is None: return _read_result("uninitialized")
            current_session = self._state["session_id"]
            if session_id is not None and session_id != current_session:
                return _read_result("session_mismatch", current_session)
            snapshot = deepcopy(self._state)
            return {"status": "ready", "session_id": current_session, "state": snapshot, "state_fingerprint": state_fingerprint(snapshot), "limitations": _LIMITATIONS}

    def compare_and_replace(self, committed_state, *, expected_session_id, expected_base_fingerprint):
        with self._lock:
            if self._state is None: return _replace_result("uninitialized")
            current = deepcopy(self._state); session = current["session_id"]; previous = state_fingerprint(current)
            if expected_session_id != session: return _replace_result("session_mismatch", session, previous)
            if expected_base_fingerprint != previous: return _replace_result("stale_state", session, previous)
            if not isinstance(committed_state, dict): return _replace_result("invalid_committed_state", session, previous)
            if committed_state.get("state_version") != STATE_MODEL_VERSION: return _replace_result("unsupported_state_version", session, previous)
            if not _valid_state(committed_state): return _replace_result("invalid_committed_state", session, previous)
            if committed_state.get("session_id") != session: return _replace_result("session_mismatch", session, previous)
            candidate = deepcopy(committed_state); current_seq, candidate_seq = current.get("last_applied_observation_sequence"), candidate.get("last_applied_observation_sequence")
            current_digest, candidate_digest = previous, state_fingerprint(candidate)
            if candidate_digest == current_digest: return _replace_result("already_current", session, previous, snapshot=current)
            if not _forward_sequence(current_seq, candidate_seq): return _replace_result("sequence_regression", session, previous)
            self._state = candidate
            return _replace_result("replaced", session, previous, current_digest=candidate_digest, snapshot=candidate)

    def capture_rollback_snapshot(self, session_id=None):
        """Private process-local recovery snapshot; never serialized or UI-exposed."""
        read = self.read_snapshot(session_id)
        if read["status"] != "ready": return read
        return {"status": "ready", "session_id": read["session_id"], "state": read["state"], "state_fingerprint": read["state_fingerprint"], "limitations": _LIMITATIONS}

    def compare_and_restore_snapshot(self, *, expected_current_fingerprint, rollback_snapshot):
        """Rollback-only CAS: permits a validated previous sequence after target CAS."""
        if not isinstance(rollback_snapshot, dict) or rollback_snapshot.get("status") != "ready": return _replace_result("invalid_rollback_snapshot")
        state = rollback_snapshot.get("state"); session = rollback_snapshot.get("session_id")
        if not _valid_state(state) or state_fingerprint(state) != rollback_snapshot.get("state_fingerprint"): return _replace_result("invalid_rollback_snapshot")
        with self._lock:
            if self._state is None: return _replace_result("uninitialized")
            current = deepcopy(self._state); current_fp = state_fingerprint(current)
            if current_fp != expected_current_fingerprint: return _replace_result("rollback_cas_conflict", current.get("session_id"), current_fp)
            if current.get("session_id") != session or state.get("session_id") != session: return _replace_result("rollback_session_mismatch", current.get("session_id"), current_fp)
            self._state = deepcopy(state)
            return _replace_result("rollback_restored", session, current_fp, current_digest=state_fingerprint(state), snapshot=state)

    def start_new_session(self, initial_state, new_session_id):
        """Explicitly replace the current namespace; no history or implicit IDs."""
        with self._lock:
            if not isinstance(new_session_id, str) or not new_session_id or not _valid_state(initial_state) or initial_state.get("session_id") != new_session_id:
                return _replace_result("invalid_committed_state")
            self._state = deepcopy(initial_state)
            snapshot = deepcopy(self._state)
            return _replace_result("session_started", new_session_id, None, current_digest=state_fingerprint(snapshot), snapshot=snapshot)


_LIMITATIONS = ["process_local_only", "single_current_session", "no_ui_integration", "no_persistence", "no_provider_calls"]


def _valid_state(value):
    if not isinstance(value, dict) or value.get("state_version") != STATE_MODEL_VERSION or not isinstance(value.get("session_id"), str) or not value["session_id"]: return False
    if not all(isinstance(value.get(key), dict) for key in ("self_side", "opponent_side", "field")): return False
    sequence = value.get("last_applied_observation_sequence")
    return (
        (sequence is None or (isinstance(sequence, int) and not isinstance(sequence, bool) and sequence >= 0))
        and validate_battle_state_unknown_markers(value)
    )


def _forward_sequence(current, candidate):
    if current is None: return isinstance(candidate, int) and not isinstance(candidate, bool) and candidate >= 1
    return isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > current


def _read_result(status, session_id=None):
    return {"status": status, "session_id": session_id, "state": None, "state_fingerprint": None, "limitations": _LIMITATIONS}


def _replace_result(status, session_id=None, previous=None, current_digest=None, snapshot=None):
    return {"status": status, "previous_fingerprint": previous, "current_fingerprint": current_digest if current_digest is not None else previous, "session_id": session_id, "state_snapshot": deepcopy(snapshot) if snapshot is not None else None, "limitations": _LIMITATIONS}
