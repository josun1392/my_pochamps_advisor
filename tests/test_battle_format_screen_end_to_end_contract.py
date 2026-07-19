import pytest

from llm.advisor_battle_state_context import build_context_modified_damage_estimate


def test_trusted_format_applies_one_screen_once() -> None:
    estimate = {"calculation_status": "resolved", "damage_class": "physical", "move_type": "normal", "damage_rolls": [100] * 16}
    field = {"current_field": {"weather": "none", "side_effects": [{"side": "opponent", "effect": "reflect"}, {"side": "opponent", "effect": "aurora-veil"}]}}
    singles = build_context_modified_damage_estimate(estimate, None, field, {"battle_format": "singles"})
    doubles = build_context_modified_damage_estimate(estimate, None, field, {"battle_format": "doubles"})
    assert singles["damage_rolls"] == [50] * 16 and singles["screen_modifier"]["screen"] == "reflect"
    assert doubles["damage_rolls"] == [67] * 16 and doubles["screen_modifier"]["numerator"] == 2


@pytest.mark.parametrize("category,screen", [("physical", "reflect"), ("special", "light-screen"), ("physical", "aurora-veil"), ("special", "aurora-veil")])
@pytest.mark.parametrize("battle_format,expected", [("singles", 50), ("doubles", 67)])
def test_defender_screens_use_the_confirmed_format(category: str, screen: str, battle_format: str, expected: int) -> None:
    result = build_context_modified_damage_estimate(
        {"calculation_status": "resolved", "damage_class": category, "move_type": "normal", "damage_rolls": [100] * 16},
        None,
        {"current_field": {"weather": "none", "side_effects": [{"side": "opponent", "effect": screen}]}},
        {"current_battle_format": {"battle_format": battle_format}},
    )
    assert result["damage_rolls"] == [expected] * 16


def test_attacker_side_screen_is_ignored_and_missing_format_is_unavailable() -> None:
    estimate = {"calculation_status": "resolved", "damage_class": "physical", "move_type": "normal", "damage_rolls": [100] * 16}
    attacker_screen = build_context_modified_damage_estimate(estimate, None, {"current_field": {"weather": "none", "side_effects": [{"side": "self", "effect": "reflect"}]}}, None)
    missing = build_context_modified_damage_estimate(estimate, None, {"current_field": {"weather": "none", "side_effects": [{"side": "opponent", "effect": "reflect"}]}}, None)
    assert attacker_screen["damage_rolls"] == [100] * 16
    assert missing["calculation_status"] == "unavailable" and missing["reason"] == "missing_battle_format_for_screen"
