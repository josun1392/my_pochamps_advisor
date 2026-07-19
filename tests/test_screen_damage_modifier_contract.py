from llm.advisor_battle_state_context import build_context_modified_damage_estimate


def test_screen_requires_trusted_battle_format_instead_of_assuming_singles() -> None:
    estimate = {"calculation_status": "resolved", "damage_class": "physical", "move_type": "normal", "damage_rolls": [100] * 16}
    field = {"current_field": {"weather": "none", "side_effects": [{"side": "opponent", "effect": "reflect"}]}}
    result = build_context_modified_damage_estimate(estimate, None, field)
    assert result["calculation_status"] == "unavailable"
    assert result["reason"] == "missing_battle_format_for_screen"
