import pytest
from llm.advisor_battle_state_context import build_fixed_damage_assessment


@pytest.mark.parametrize("move,rule", [("seismic-toss", "attacker-level"), ("night-shade", "attacker-level"), ("dragon-rage", "literal-40"), ("sonic-boom", "literal-20")])
def test_supported_fixed_moves_have_explicit_rules(move, rule):
    result = build_fixed_damage_assessment({"move_id": move}, None, attacker_level_context={"level": 50})
    assert result["rule"] == rule and result["status"] == "resolved"


@pytest.mark.parametrize("move", ["endeavor", "final-gambit", "psywave", "counter", "mirror-coat", "metal-burst", "bide", "comeuppance", "fissure", "guillotine", "horn-drill", "sheer-cold"])
def test_special_fixed_rules_are_explicitly_unavailable(move):
    assert build_fixed_damage_assessment({"move_id": move}, None)["reason"] == "unsupported_fixed_damage_rule"


def test_ordinary_move_has_no_fixed_result():
    assert build_fixed_damage_assessment({"move_id": "tackle"}, None) is None
