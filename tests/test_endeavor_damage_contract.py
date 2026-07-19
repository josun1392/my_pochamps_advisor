from llm.advisor_battle_state_context import build_hp_based_special_damage_assessment


def _hp(self_hp, opponent_hp):
    return {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 200}, {"side": "opponent", "current_hp": opponent_hp, "maximum_hp": 200}]}


def test_endeavor_lowers_only_higher_target_hp():
    result = build_hp_based_special_damage_assessment({"move_id": "endeavor"}, _hp(40, 120))
    assert (result["damage"], result["opponent_resulting_hp"], result["status"]) == (80, 40, "resolved")


def test_endeavor_equal_or_lower_target_is_no_effect():
    assert build_hp_based_special_damage_assessment({"move_id": "endeavor"}, _hp(40, 40))["reason"] == "target_hp_not_higher"
    assert build_hp_based_special_damage_assessment({"move_id": "endeavor"}, _hp(40, 30))["status"] == "no_effect"
