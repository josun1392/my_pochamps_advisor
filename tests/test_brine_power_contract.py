from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_brine_exact_half_doubles():
    hp = {"current_hp": [{"side": "opponent", "current_hp": 100, "maximum_hp": 200}]}
    assert build_binary_condition_power_assessment({"move_id": "brine"}, None, hp)["effective_power"] == 130
