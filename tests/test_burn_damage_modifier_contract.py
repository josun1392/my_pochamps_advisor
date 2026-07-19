from llm.advisor_battle_state_context import build_context_modified_damage_estimate


def _estimate(category: str = "physical") -> dict:
    return {"calculation_status": "resolved", "damage_class": category, "move_type": "normal", "level": 50, "power": 80, "offensive_stat": 200, "defensive_stat": 150, "damage_rolls": [100] * 16}


def test_confirmed_burn_halves_only_physical_damage() -> None:
    context = {"current_conditions": [{"side": "self", "condition_type": "burn"}]}
    assert build_context_modified_damage_estimate(_estimate(), context, None)["damage_rolls"] == [50] * 16
    assert build_context_modified_damage_estimate(_estimate("special"), context, None)["damage_rolls"] == [100] * 16
