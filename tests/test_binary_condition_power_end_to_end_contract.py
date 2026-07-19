from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_none_condition_keeps_base_power():
    c = {"current_conditions": [{"side": "opponent", "condition_type": "none"}]}
    assert build_binary_condition_power_assessment({"move_id": "hex"}, c, None)["effective_power"] == 65
