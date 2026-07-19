from llm.advisor_battle_state_context import build_context_modified_damage_estimate, build_hp_ko_assessment


def test_context_modified_rolls_recalculate_hp_ko() -> None:
    estimate = build_context_modified_damage_estimate(
        {"calculation_status": "resolved", "attacker_side": "self", "defender_side": "opponent", "move": "tackle", "damage_class": "physical", "move_type": "normal", "damage_rolls": [100] * 16},
        {"current_conditions": [{"side": "self", "condition_type": "burn"}]}, None,
    )
    hp = {"current_hp": [{"side": "opponent", "current_hp": 75, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp"}]}
    assessment = build_hp_ko_assessment(estimate, hp)
    assert assessment["min_damage"] == assessment["max_damage"] == 50
    assert assessment["ohko"]["status"] == "impossible"
