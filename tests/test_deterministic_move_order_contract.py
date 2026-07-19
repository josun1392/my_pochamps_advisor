import pytest
from llm.advisor_battle_state_context import build_deterministic_move_order_assessment


def _stats(a, b):
    return {"current_final_stats": [{"side": side, "stat": "speed", "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"} for side, value in (("self", a), ("opponent", b))]}


@pytest.mark.parametrize("self_priority,opponent_priority,expected", [(1, 0, "self_first"), (0, 1, "opponent_first")])
def test_priority_advantage_resolves_without_speed(self_priority, opponent_priority, expected):
    result = build_deterministic_move_order_assessment(None, None, None, {"move_id": "a", "priority": self_priority}, {"move_id": "b", "priority": opponent_priority})
    assert result["result"] == expected and result["reason"] == "priority_advantage"


@pytest.mark.parametrize("self_speed,opponent_speed,expected", [(120, 100, "self_first"), (100, 120, "opponent_first"), (100, 100, "tie")])
def test_equal_priority_speed_and_tie(self_speed, opponent_speed, expected):
    result = build_deterministic_move_order_assessment(_stats(self_speed, opponent_speed), None, None, {"move_id": "a", "priority": 0}, {"move_id": "b", "priority": 0})
    assert result["result"] == expected
