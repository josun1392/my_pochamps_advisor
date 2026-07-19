from llm.advisor_battle_state_context import build_context_modified_damage_estimate


def test_trusted_format_applies_one_screen_once() -> None:
    estimate = {"calculation_status": "resolved", "damage_class": "physical", "move_type": "normal", "damage_rolls": [100] * 16}
    field = {"current_field": {"weather": "none", "side_effects": [{"side": "opponent", "effect": "reflect"}, {"side": "opponent", "effect": "aurora-veil"}]}}
    singles = build_context_modified_damage_estimate(estimate, None, field, {"battle_format": "singles"})
    doubles = build_context_modified_damage_estimate(estimate, None, field, {"battle_format": "doubles"})
    assert singles["damage_rolls"] == [50] * 16 and singles["screen_modifier"]["screen"] == "reflect"
    assert doubles["damage_rolls"] == [67] * 16 and doubles["screen_modifier"]["numerator"] == 2
