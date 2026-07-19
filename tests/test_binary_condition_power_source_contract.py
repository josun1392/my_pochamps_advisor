from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_missing_condition_unavailable():
    assert build_binary_condition_power_assessment({"move_id": "hex"}, None, None)["reason"] == "missing_opponent_condition"
