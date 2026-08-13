"""Reducer-owned current-type authority is explicit, identity-bound, and frozen."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import CURRENT_TYPE_SOURCE, SWITCH_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = "raichu"
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _type(boundary, types, *, turn=1, session="s", pokemon_id="pikachu", slot=0):
    return boundary.confirm(event_kind="current_type_observed", payload={"types": types}, session_id=session, source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=slot, pokemon_id=pokemon_id, turn_number=turn)


def _frozen(manager, *, active="pikachu", slot=0):
    runtime = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    return build_turn_snapshot_from_battle_input({
        "pokemon": {"my_active": {"slot_index": slot, "name_en": active}, "opponent_active": {"slot_index": 0, "name_en": "eevee"}},
        "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}},
        "current_state_session_id": "s", "runtime_advice_state": runtime,
    }).to_dict()["current_state"]


def test_current_type_starts_unknown_then_explicit_observation_replaces_same_identity():
    manager, boundary = _manager(), _boundary()
    initial = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert initial["self"]["active_pokemon"]["current_type"] == {"status": "unknown"}
    _apply(manager, _type(boundary, ["poison"], turn=3))
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["current_type"] == ["poison"]
    _apply(manager, _type(boundary, ["water"], turn=4))
    runtime = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert runtime["self"]["active_pokemon"]["current_type"] == {"status": "known", "value": ["water"]}


def test_type_observation_rejects_stale_session_and_identity_mismatch():
    manager, boundary = _manager(), _boundary()
    assert _type(boundary, ["poison"], session="stale")["status"] == "stale_session"
    assert _type(boundary, ["poison"], pokemon_id="raichu")["status"] == "invalid_provenance"
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["current_type"] == {"knowledge": "unknown"}


def test_switching_identity_never_inherits_current_type_and_frozen_context_is_detached():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _type(boundary, ["poison"], turn=2))
    before = _frozen(manager)
    assert before["current_type_context"]["current_types"][0]["types"] == ["poison"]
    _apply(manager, boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu"}, session_id="s", source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu"))
    after = _frozen(manager, active="raichu", slot=1)
    assert after["runtime_advice_state"]["self"]["active_pokemon"]["current_type"] == {"status": "unknown"}
    assert "current_type_context" not in after
    assert before["current_type_context"]["current_types"][0]["types"] == ["poison"]
