from llm.advisor_battle_state_context import build_deterministic_calculation_context


def test_consecutive_use_assessment_is_included_without_stat_inputs():
    result = build_deterministic_calculation_context(None, selected_move={"move_id": "echoed-voice"}, consecutive_use_context={"echoed_voice_consecutive_uses": 3})
    assert result["consecutive_use_power_assessment"]["effective_power"] == 120
