import pytest

from llm.advisor_battle_state_context import build_deterministic_move_order_assessment


def test_priority_must_be_explicit_trusted_move_metadata() -> None:
    result = build_deterministic_move_order_assessment(None, None, None, {"move_id": "quick-attack", "priority": 1}, None)
    assert result["result"] == "unavailable" and result["reason"] == "missing_opponent_move_priority"
    with pytest.raises(AssertionError):
        assert build_deterministic_move_order_assessment(None, None, None, {"move_id": "tackle", "priority": "0"}, {"move_id": "tackle", "priority": 0})["result"] != "unavailable"
