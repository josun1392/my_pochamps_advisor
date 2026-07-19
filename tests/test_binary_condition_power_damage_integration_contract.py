from llm.advisor_battle_state_context import build_binary_condition_power_assessment


def test_ordinary_move_unaffected():
    assert build_binary_condition_power_assessment({"move_id": "tackle"}, None, None) is None
