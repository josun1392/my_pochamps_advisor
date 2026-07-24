"""Pure provenance policy for legacy deterministic contexts; no provider is used."""
from copy import deepcopy

from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle


REPOSITORY = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}


def _entry(side="self", slot=0, pokemon="pikachu", session="s", **extra):
    return {"side": side, "slot_index": slot, "current_hp": 50, "maximum_hp": 100, "provenance": {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": session, "source": "user_confirmed_current_hp", "trust": "user_confirmed_current"}, **extra}


def _battle(entry):
    return {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}, "current_hp_context": {"current_hp": [entry]}, "field_state_context": {"current_field": {"weather": "rain"}}}


def _cycle(entry):
    return prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=_battle(entry), move_repository=REPOSITORY)


def test_correct_provenance_is_serialized_for_candidate_and_structured_summary():
    cycle = _cycle(_entry())
    state = cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"]["current_state"]
    assert state["current_hp_context"]["current_hp"][0]["provenance"]["pokemon_id"] == "pikachu"
    assert state["field_state_context"]["current_field"]["weather"] == "rain"


def test_wrong_slot_identity_or_session_is_excluded_without_auto_current_assignment():
    for entry in (_entry(slot=9), _entry(pokemon="mew"), _entry(session="old"), {"side": "self", "current_hp": 50}):
        cycle = _cycle(entry)
        state = cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"].get("current_state", {})
        assert "current_hp_context" not in state


def test_legacy_context_is_not_promoted_and_original_mutation_cannot_reenter_snapshot():
    legacy = {"side": "self", "current_hp": 50, "maximum_hp": 100}
    battle = _battle(legacy)
    cycle = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=battle, move_repository=REPOSITORY)
    legacy["current_hp"] = 1
    state = deepcopy(cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"].get("current_state", {}))
    assert "current_hp_context" not in state and state["field_state_context"]["current_field"]["weather"] == "rain"
