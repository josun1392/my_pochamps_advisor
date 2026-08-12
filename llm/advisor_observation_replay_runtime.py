"""Private session-bound owner for replay state, ledger, and envelope helpers."""
from copy import deepcopy

from llm.advisor_battle_state_store import BattleStateStore, _valid_state
from llm.advisor_observation_replay_coordinator import ObservationReplayCoordinator
from llm.advisor_observation_replay_persistence import ObservationReplayPersistence


_ALLOWED_STATE_KEYS = {
    "state_version", "session_id", "self_side", "opponent_side", "field",
    "last_applied_observation_sequence", "q12", "ranking",
    "last_applied_batch_fingerprint", "source_replay_policy_version",
    "last_commit_provenance", "same_turn_event_context", "first_end_of_turn_context",
}
_REQUIRED_STATE_KEYS = {
    "state_version", "session_id", "self_side", "opponent_side", "field",
    "last_applied_observation_sequence",
}


class ObservationReplayRuntime:
    """One immutable-session, process-local replay recovery unit.

    It deliberately exposes only detached delegation.  Persistence commands,
    rollback recovery, session rollover, UI, worker, and provider boundaries
    remain outside this owner.
    """

    def __init__(self, initial_state, *, move_repository=None):
        self._store = BattleStateStore(initial_state)
        self._session_id = deepcopy(initial_state["session_id"])
        self._coordinator = ObservationReplayCoordinator(self._store, move_repository=move_repository)
        self._persistence = ObservationReplayPersistence()

    @classmethod
    def create(cls, initial_state, *, move_repository=None):
        """Create a runtime only from a valid detached battle-state-v1 mapping."""
        if not _valid_initial_state(initial_state):
            return {"status": "invalid_initial_state", "runtime": None, "session_id": None}
        runtime = cls(deepcopy(initial_state), move_repository=move_repository)
        return {"status": "ready", "runtime": runtime, "session_id": runtime.session_id}

    @property
    def session_id(self):
        return self._session_id

    def read_state(self):
        return deepcopy(self._store.read_snapshot(self._session_id))

    def read_applied_ledger(self):
        return deepcopy(self._coordinator.export_applied_ledger(self._session_id))

    def preview(self, observation_snapshot):
        return deepcopy(self._coordinator.preview(deepcopy(observation_snapshot)))

    def apply(self, observation_snapshot):
        return deepcopy(self._coordinator.apply_confirmed_observations(deepcopy(observation_snapshot)))

    def export_envelope(self):
        return deepcopy(self._persistence.export_envelope(self._store, self._coordinator, self._session_id))

    def validate_envelope(self, envelope):
        return deepcopy(self._persistence.validate(deepcopy(envelope)))

    def _persistence_command_context(self):
        """Private bounded seam for the matching persistence command owner."""
        return {
            "runtime_identity": id(self),
            "session_id": self._session_id,
            "store": self._store,
            "coordinator": self._coordinator,
            "persistence": self._persistence,
        }


def _valid_initial_state(value):
    return (
        isinstance(value, dict)
        and _REQUIRED_STATE_KEYS <= set(value)
        and set(value) <= _ALLOWED_STATE_KEYS
        and _valid_state(value)
    )
