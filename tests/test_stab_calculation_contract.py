from llm.advisor_battle_state_context import build_deterministic_calculation_context


def _context(*, attacker_types: list[str], move_type: str = "fire") -> dict:
    return build_deterministic_calculation_context(
        {"current_final_stats": [
            {"side": "self", "stat": "special-attack", "value": 200, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
            {"side": "opponent", "stat": "special-defense", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
        ]},
        None, {"move_id": "flamethrower", "category": "special", "power": 90, "type": move_type}, None,
        {"my_active": {"types": attacker_types}, "opponent_active": {"types": ["normal"]}},
    )


def test_stab_is_a_plain_three_over_two_modifier() -> None:
    estimate = _context(attacker_types=["fire"])["damage_estimates"][0]
    assert estimate["stab"] == {"applied": True, "numerator": 3, "denominator": 2}
    assert estimate["calculation_scope"] == "base_damage_stage_stab_type"


def test_non_stab_is_neutral() -> None:
    estimate = _context(attacker_types=["water"])["damage_estimates"][0]
    assert estimate["stab"] == {"applied": False, "numerator": 1, "denominator": 1}
