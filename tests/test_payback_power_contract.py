from llm.advisor_battle_state_context import build_turn_event_power_assessment


def test_observed_action_order_only():
    assert build_turn_event_power_assessment({"move_id": "payback"}, {"target_acted_before_user": True})["effective_power"] == 100
    assert build_turn_event_power_assessment({"move_id": "payback"}, {"target_acted_before_user": False})["effective_power"] == 50
