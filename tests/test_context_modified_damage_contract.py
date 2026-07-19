from llm.advisor_battle_state_context import build_context_modified_damage_estimate


def test_context_rolls_preserve_type_aware_immunity() -> None:
    estimate = {"calculation_status": "resolved", "damage_class": "physical", "move_type": "normal", "damage_rolls": [0] * 16}
    result = build_context_modified_damage_estimate(
        estimate,
        {"current_conditions": [{"side": "self", "condition_type": "burn"}]},
        {"current_field": {"weather": "rain", "side_effects": []}},
    )
    assert result["calculation_scope"] == "base_damage_stage_stab_type_context"
    assert result["damage_rolls"] == [0] * 16
