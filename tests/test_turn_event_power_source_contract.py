from llm.advisor_battle_state_context import build_turn_event_power_assessment


def test_missing_event_is_unavailable():
    assert build_turn_event_power_assessment({"move_id": "payback"}, None)["reason"] == "missing_current_turn_action_order"
