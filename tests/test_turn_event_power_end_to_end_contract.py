from llm.advisor_battle_state_context import build_turn_event_power_assessment


def test_assurance_missing_event_unavailable():
    assert build_turn_event_power_assessment({"move_id": "assurance"}, None)["reason"] == "missing_current_turn_target_hp_loss"
