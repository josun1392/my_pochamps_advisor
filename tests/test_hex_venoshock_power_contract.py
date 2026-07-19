from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_hex_and_venoshock_conditions():
    poison = {"current_conditions": [{"side": "opponent", "condition_type": "poison"}]}
    burn = {"current_conditions": [{"side": "opponent", "condition_type": "burn"}]}
    assert build_binary_condition_power_assessment({"move_id": "hex"}, burn, None)["effective_power"] == 130
    assert build_binary_condition_power_assessment({"move_id": "venoshock"}, poison, None)["effective_power"] == 130
