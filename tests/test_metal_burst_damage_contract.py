from llm.advisor_battle_state_context import build_observed_damage_counter_assessment
from llm.advisor_client import normalize_observed_previous_damage_confirmation


def test_metal_burst_floors_three_halves_and_reports_no_ko():
    observed = normalize_observed_previous_damage_confirmation({"damage": 61, "damage_category": "physical", "damage_kind": "direct_move_damage", "source_side": "opponent", "target_side": "self"})
    result = build_observed_damage_counter_assessment({"move_id": "metal-burst"}, observed, {"current_hp": [{"side": "opponent", "current_hp": 100}]})
    assert result["returned_damage"] == 91 and result["ko_status"] == "no_ko"


def test_counter_moves_do_not_fall_back_to_normal_damage_estimates():
    from llm.advisor_battle_state_context import build_deterministic_calculation_context
    result = build_deterministic_calculation_context(None, selected_move={"move_id": "counter"})
    assert result["observed_damage_counter_assessment"]["status"] == "unavailable"
