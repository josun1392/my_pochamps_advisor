from llm.advisor_battle_state_context import build_hp_based_special_damage_assessment


def _hp(self_hp, opponent_hp):
    return {"current_hp": [{"side": "self", "current_hp": self_hp, "maximum_hp": 200}, {"side": "opponent", "current_hp": opponent_hp, "maximum_hp": 200}]}


def test_final_gambit_caps_actual_damage_and_self_faints():
    result = build_hp_based_special_damage_assessment({"move_id": "final-gambit"}, _hp(120, 100))
    assert (result["damage"], result["actual_damage"], result["opponent_resulting_hp"], result["self_faint_status"]) == (120, 100, 0, "guaranteed_self_faint")


def test_missing_and_fainted_hp_boundaries():
    assert build_hp_based_special_damage_assessment({"move_id": "final-gambit"}, None)["reason"] == "missing_self_current_hp"
    assert build_hp_based_special_damage_assessment({"move_id": "final-gambit"}, _hp(0, 100))["status"] == "not_applicable"
