from llm.advisor_battle_state_context import build_turn_event_power_assessment


def test_current_turn_hp_loss_only():
    assert build_turn_event_power_assessment({"move_id": "assurance"}, {"target_lost_hp_this_turn": True})["effective_power"] == 120
    assert build_turn_event_power_assessment({"move_id": "assurance"}, {"target_lost_hp_this_turn": False})["effective_power"] == 60
