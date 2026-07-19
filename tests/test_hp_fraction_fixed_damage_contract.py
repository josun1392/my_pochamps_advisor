import pytest
from llm.advisor_battle_state_context import build_fixed_damage_assessment


def _hp(current): return {"current_hp": [{"side": "opponent", "current_hp": current, "maximum_hp": 101}]}


@pytest.mark.parametrize("move", ["super-fang", "natures-madness", "ruination"])
def test_current_hp_half_moves_floor_odd_hp(move):
    result = build_fixed_damage_assessment({"move_id": move}, _hp(101))
    assert result["damage"] == 50 and result["resulting_hp"] == 51


def test_missing_and_fainted_defender_hp_boundaries():
    assert build_fixed_damage_assessment({"move_id": "super-fang"}, None)["reason"] == "missing_defender_current_hp"
    assert build_fixed_damage_assessment({"move_id": "super-fang"}, _hp(0))["status"] == "not_applicable"
