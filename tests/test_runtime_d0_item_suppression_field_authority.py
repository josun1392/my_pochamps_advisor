from copy import deepcopy

from advisor.damage.field import Field
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, MAGIC_ROOM_SOURCE, USER_TRUST
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_reducer_state_model import execute_atomic_transition
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_item_suppression_field_authority import resolve_runtime_d0_item_suppression_field_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state() -> dict:
    return create_unknown_bootstrap_battle_state("magic-room-d0", "self-a", "opponent-a")["state"]


def _owner(state: dict) -> dict:
    return {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": "self-a"}


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _authority(state: dict, **kwargs) -> dict:
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    return resolve_runtime_d0_item_suppression_field_authority(strategy_d0=d0, runtime_snapshot=snapshot, **kwargs)


def _observe(state: dict, status: str, sequence: int = 1) -> None:
    state["field"]["magic_room_status"] = status
    state["field"]["magic_room_status_provenance"] = {"event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation", "source_observation_id": f"mr-{sequence}", "source_sequence": sequence}


def test_three_state_projection_and_default_false_is_not_authority() -> None:
    assert _authority(_state())["state"] == "unknown"
    inactive = _state(); _observe(inactive, "inactive")
    absent = _authority(inactive)
    assert absent["status"] == "resolved" and absent["state"] == "known_absent" and absent["item_effects_suppressed"] is False
    active = _state(); _observe(active, "active")
    result = _authority(active)
    assert result["status"] == "resolved" and result["state"] == "active" and result["item_effects_suppressed"] is True
    assert Field().is_magic_room is False and _authority(_state())["state"] == "unknown"


def test_binding_and_provenance_fail_closed() -> None:
    state = _state(); _observe(state, "active")
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    stale = deepcopy(state); _observe(stale, "inactive", 2)
    assert resolve_runtime_d0_item_suppression_field_authority(strategy_d0=d0, runtime_snapshot=_snapshot(stale))["status"] == "rejected"
    foreign = _snapshot(state); foreign["session_id"] = "other"
    assert resolve_runtime_d0_item_suppression_field_authority(strategy_d0=d0, runtime_snapshot=foreign)["status"] == "rejected"
    assert resolve_runtime_d0_item_suppression_field_authority(strategy_d0=d0, runtime_snapshot=snapshot, field_id="trick-room")["status"] == "rejected"
    state["field"]["magic_room_status_provenance"]["trust"] = "untrusted"
    assert _authority(state)["state"] == "unknown"


def test_newer_reducer_owned_inactive_observation_supersedes_active_without_mutation() -> None:
    state = _state(); _observe(state, "active", 1)
    before = deepcopy(state)
    assert _authority(state)["state"] == "active"
    assert state == before
    _observe(state, "inactive", 2)
    assert _authority(state)["state"] == "known_absent"


def test_production_observation_replay_owns_active_then_inactive_lifecycle() -> None:
    state = _state()
    boundary = LifecycleConfirmationBoundary(state["session_id"], {})
    active = boundary.confirm(event_kind="magic_room_field_observed", payload={"status": "active"}, session_id=state["session_id"], source=MAGIC_ROOM_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=1)
    assert boundary.confirm(event_kind="magic_room_field_observed", payload={"status": "unknown"}, session_id=state["session_id"], source=MAGIC_ROOM_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=1)["status"] == "invalid_provenance"
    assert boundary.confirm(event_kind="magic_room_field_observed", payload={"status": "active"}, session_id=state["session_id"], source=MAGIC_ROOM_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=1, observation_id=active["observation"]["observation_id"])["status"] == "duplicate"
    inactive = boundary.confirm(event_kind="magic_room_field_observed", payload={"status": "inactive"}, session_id=state["session_id"], source=MAGIC_ROOM_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=2)
    assert active["status"] == inactive["status"] == "confirmed"
    plan = build_replay_plan(state, [active["observation"], inactive["observation"]])
    committed = execute_atomic_transition(state, plan, expected_session_id=state["session_id"])
    assert committed["status"] == "committed"
    current = committed["committed_state"]
    assert current["field"]["magic_room_status"] == "inactive"
    assert _authority(current)["state"] == "known_absent"
