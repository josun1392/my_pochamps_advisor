from llm.advisor_battle_state_context import CONSECUTIVE_USE_POWER_SCOPE, build_consecutive_use_power_assessment


def test_ordinary_move_has_no_consecutive_assessment():
    assert build_consecutive_use_power_assessment({"move_id": "tackle"}, {}) is None


def test_missing_result_has_only_contract_fields():
    assert build_consecutive_use_power_assessment({"move_id": "echoed-voice"}, {}) == {"move": "echoed-voice", "scope": CONSECUTIVE_USE_POWER_SCOPE, "status": "unavailable", "reason": "missing_echoed_voice_consecutive_uses"}
