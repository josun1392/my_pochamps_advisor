from llm.advisor_battle_state_context import build_deterministic_move_order_assessment


def _stats(self_speed: int, opponent_speed: int):
    return {"current_final_stats": [{"side": "self", "stat": "speed", "value": self_speed, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}, {"side": "opponent", "stat": "speed", "value": opponent_speed, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}]}


def test_tailwind_and_trick_room_apply_only_after_equal_priority() -> None:
    moves = ({"move_id": "tackle", "priority": 0}, {"move_id": "tackle", "priority": 0})
    field = {"current_field": {"global_effects": ["trick-room"], "side_effects": [{"side": "self", "effect": "tailwind"}]}}
    result = build_deterministic_move_order_assessment(_stats(100, 150), None, field, *moves)
    assert result["self_effective_speed"] == 200 and result["trick_room"] is True and result["result"] == "opponent_first"
