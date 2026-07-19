import pytest
from llm.advisor_battle_state_context import build_turn_event_power_assessment


@pytest.mark.parametrize("move", ["avalanche", "revenge"])
def test_current_target_direct_damage_doubles(move):
    assert build_turn_event_power_assessment({"move_id": move}, {"received_target_direct_damage": True})["effective_power"] == 120


def test_explicitly_absent_damage_keeps_base_power():
    assert build_turn_event_power_assessment({"move_id": "avalanche"}, {"received_target_direct_damage": False})["effective_power"] == 60
