from llm.advisor_battle_state_context import build_fixed_damage_assessment


def test_seismic_toss_ghost_immunity():
    result = build_fixed_damage_assessment({"move_id": "seismic-toss"}, None, {"opponent_active": {"types": ["ghost"]}}, {"level": 50})
    assert result["damage"] == 0 and result["reason"] == "type_immunity"


def test_night_shade_normal_immunity():
    result = build_fixed_damage_assessment({"move_id": "night-shade"}, None, {"opponent_active": {"types": ["normal"]}}, {"level": 50})
    assert result["damage"] == 0 and result["reason"] == "type_immunity"
