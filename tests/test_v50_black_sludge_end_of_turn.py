"""Bounded Black Sludge resolution at an explicitly observed first end-of-turn."""

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import CURRENT_TYPE_SOURCE, FIRST_END_OF_TURN_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection


def _manager(*, hp=80, item="black-sludge", fainted=False):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=100, known_item=item, fainted=fainted)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _type(manager, boundary, types):
    _apply(manager, boundary.confirm(event_kind="current_type_observed", payload={"types": types}, session_id="s", source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4))


def _phase(manager, boundary):
    _apply(manager, boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4))


def test_black_sludge_uses_reducer_owned_current_type_for_heal_and_clamps():
    manager, boundary = _manager(hp=95), _boundary()
    _type(manager, boundary, ["poison"])
    _phase(manager, boundary)
    state = manager.read_state()["state"]
    result = state["black_sludge_end_of_turn_context"][0]
    assert state["self_side"]["pokemon"][0]["current_hp"] == 100
    assert result["status"] == "complete" and result["recovery"] == 6 and result["post_hp"] == 100 and result["guaranteed_ko"] is False
    assert build_runtime_advice_state_projection(state)["runtime_advice_state"]["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 100}


def test_black_sludge_non_poison_damage_can_prove_end_of_turn_ko():
    manager, boundary = _manager(hp=10), _boundary()
    _type(manager, boundary, ["electric"])
    _phase(manager, boundary)
    state = manager.read_state()["state"]
    result = state["black_sludge_end_of_turn_context"][0]
    assert state["self_side"]["pokemon"][0]["current_hp"] == 0
    assert result["damage"] == 12 and result["post_hp"] == 0 and result["guaranteed_ko"] is True


def test_black_sludge_never_falls_back_from_unknown_type_or_unrelated_item():
    unknown, boundary = _manager(), _boundary()
    _phase(unknown, boundary)
    result = unknown.read_state()["state"]["black_sludge_end_of_turn_context"][0]
    assert result["status"] == "incomplete" and result["reason"] == "current_type_unknown"
    unrelated, boundary = _manager(item="leftovers"), _boundary()
    _type(unrelated, boundary, ["poison"])
    _phase(unrelated, boundary)
    assert unrelated.read_state()["state"].get("black_sludge_end_of_turn_context", []) == []


def test_black_sludge_does_not_apply_to_an_already_fainted_owner():
    manager, boundary = _manager(hp=0, fainted=True), _boundary()
    _type_result = boundary.confirm(event_kind="current_type_observed", payload={"types": ["poison"]}, session_id="s", source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4)
    assert _type_result["status"] == "confirmed"
    _phase(manager, boundary)
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["current_hp"] == 0
    assert state.get("black_sludge_end_of_turn_context", []) == []
