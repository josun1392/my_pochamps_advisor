from llm.advisor_battle_state_context import build_deterministic_calculation_context


def _estimate(defender_types: list[str]) -> dict:
    context = build_deterministic_calculation_context(
        {"current_final_stats": [
            {"side": "self", "stat": "special-attack", "value": 200, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
            {"side": "opponent", "stat": "special-defense", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
        ]}, None, {"move_id": "thunderbolt", "category": "special", "power": 90, "type": "electric"}, None,
        {"my_active": {"types": ["electric"]}, "opponent_active": {"types": defender_types}},
    )
    return context["damage_estimates"][0]


def test_dual_type_effectiveness_is_rational_four_times() -> None:
    assert _estimate(["water", "flying"])["type_effectiveness"] == {"numerator": 4, "denominator": 1, "label": "quadruple-effective"}


def test_immunity_is_resolved_zero_damage() -> None:
    estimate = _estimate(["ground"])
    assert estimate["type_effectiveness"]["numerator"] == 0
    assert estimate["min_damage"] == estimate["max_damage"] == 0
