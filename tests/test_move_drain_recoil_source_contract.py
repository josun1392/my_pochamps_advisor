from llm.advisor_battle_state_context import build_drain_recoil_assessment


def test_drain_metadata_is_integer_and_exceptional_recoil_is_not_guessed() -> None:
    rolls = {"calculation_status": "resolved", "damage_rolls": [100] * 16}
    hp = {"current_hp": [{"side": "opponent", "current_hp": 100, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    assert build_drain_recoil_assessment(rolls, {"move_id": "x", "drain": "50"}, hp)["calculation_status"] == "unavailable"
    assert build_drain_recoil_assessment(rolls, {"move_id": "struggle", "drain": -25}, hp)["reason"] == "unsupported_recoil_rule"
