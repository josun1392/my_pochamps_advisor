from llm.advisor_battle_state_context import build_battle_counter_power_assessment


def test_missing_rage_fist_counter_is_unavailable():
    result = build_battle_counter_power_assessment({"move_id": "rage-fist"}, None)
    assert result["reason"] == "missing_rage_fist_hits_received"


def test_counter_rejects_bool_negative_and_non_integer_values():
    for value in (True, -1, 1.0, "1"):
        result = build_battle_counter_power_assessment({"move_id": "rage-fist"}, {"rage_fist_hits_received": value})
        assert result["reason"] == "invalid_battle_counter"
