from llm.advisor_battle_state_context import build_deterministic_calculation_context


def test_battle_counter_resolved_result_is_present_without_stat_inputs():
    result = build_deterministic_calculation_context(None, selected_move={"move_id": "rage-fist"}, battle_counter_context={"rage_fist_hits_received": 1})
    assert result["battle_counter_power_assessment"]["effective_power"] == 100


def test_ordinary_move_has_no_battle_counter_assessment():
    assert build_deterministic_calculation_context(None, selected_move={"move_id": "tackle"}, battle_counter_context={"rage_fist_hits_received": 1}) is None
