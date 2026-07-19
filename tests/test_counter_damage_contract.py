from llm.advisor_battle_state_context import build_observed_damage_counter_assessment
from llm.advisor_client import normalize_observed_previous_damage_confirmation


def _observed(category="physical", damage=60):
    return normalize_observed_previous_damage_confirmation({"damage": damage, "damage_category": category, "damage_kind": "direct_move_damage", "source_side": "opponent", "target_side": "self"})


def test_counter_returns_double_physical_damage_and_caps_hp():
    result = build_observed_damage_counter_assessment({"move_id": "counter"}, _observed(), {"current_hp": [{"side": "opponent", "current_hp": 100}]})
    assert result["returned_damage"] == 120 and result["actual_damage"] == 100 and result["ko_status"] == "guaranteed_ko"


def test_counter_special_is_no_effect_and_missing_hp_is_partial():
    assert build_observed_damage_counter_assessment({"move_id": "counter"}, _observed("special"), None)["reason"] == "previous_damage_not_physical"
    assert build_observed_damage_counter_assessment({"move_id": "counter"}, _observed(), None)["returned_damage"] == 120


def test_counter_ghost_immunity_and_fainted_target():
    immune = build_observed_damage_counter_assessment({"move_id": "counter"}, _observed(), None, {"opponent_active": {"types": ["ghost"]}})
    fainted = build_observed_damage_counter_assessment({"move_id": "counter"}, _observed(), {"current_hp": [{"side": "opponent", "current_hp": 0}]})
    assert immune["reason"] == "type_immunity" and fainted["reason"] == "target_already_fainted"
