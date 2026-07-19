from llm.advisor_battle_state_context import build_drain_recoil_assessment


def test_recoil_ko_uses_damage_rolls_and_zero_hp_is_not_applicable() -> None:
    hp = {"current_hp": [{"side": "opponent", "current_hp": 100, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}, {"side": "self", "current_hp": 30, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    result = build_drain_recoil_assessment({"calculation_status": "resolved", "damage_rolls": [90, 100] * 8}, {"move_id": "brave-bird", "drain": -33}, hp)
    assert result["recoil_ko_status"] == "possible_recoil_ko"
