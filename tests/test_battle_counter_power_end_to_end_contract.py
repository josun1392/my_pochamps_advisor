from llm.advisor_battle_state_context import BATTLE_COUNTER_POWER_SCOPE, build_battle_counter_power_assessment


def test_counter_result_uses_explicit_scope_and_never_falls_back():
    result = build_battle_counter_power_assessment({"move_id": "last-respects"}, {})
    assert result == {"move": "last-respects", "scope": BATTLE_COUNTER_POWER_SCOPE, "status": "unavailable", "reason": "missing_last_respects_fainted_allies"}
