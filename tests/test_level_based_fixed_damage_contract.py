import pytest
from llm.advisor_battle_state_context import build_fixed_damage_assessment


def test_level_based_damage_and_ko():
    result = build_fixed_damage_assessment({"move_id": "seismic-toss"}, {"current_hp": [{"side": "opponent", "current_hp": 50, "maximum_hp": 200}]}, attacker_level_context={"level": 50})
    assert result["damage"] == 50 and result["ko_status"] == "guaranteed_ko"


def test_level_based_no_ko():
    assert build_fixed_damage_assessment({"move_id": "night-shade"}, {"current_hp": [{"side": "opponent", "current_hp": 51, "maximum_hp": 200}]}, attacker_level_context={"level": 50})["ko_status"] == "no_ko"


@pytest.mark.parametrize("level,reason", [(None, "missing_attacker_level"), (0, "invalid_attacker_level"), (101, "invalid_attacker_level"), (True, "invalid_attacker_level"), (50.0, "invalid_attacker_level")])
def test_missing_or_invalid_level_is_unavailable(level, reason):
    context = {} if level is None else {"level": level}
    assert build_fixed_damage_assessment({"move_id": "seismic-toss"}, None, attacker_level_context=context)["reason"] == reason
