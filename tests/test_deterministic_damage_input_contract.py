from __future__ import annotations

from llm.advisor_battle_state_context import build_deterministic_calculation_context


def _final(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _stage(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "stage": value, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}


def test_damage_uses_only_stage_adjusted_final_stats_and_selected_move_metadata() -> None:
    context = build_deterministic_calculation_context(
        {"current_final_stats": [_final("self", "attack", 200), _final("opponent", "defense", 150)]},
        {"current_stages": [_stage("self", "attack", 1), _stage("opponent", "defense", 0)]},
        {"move_id": "tackle", "category": "physical", "power": 40},
    )
    assert context is not None
    estimate = context["damage_estimates"][0]
    assert estimate["offensive_stat"] == 300
    assert estimate["defensive_stat"] == 150
    assert estimate["level"] == 50
    assert estimate["calculation_scope"] == "base_damage_stage_only"
    assert estimate["excluded_modifiers"] == ["stab", "type-effectiveness", "critical-hit", "burn", "weather", "terrain", "screens", "item", "ability", "spread", "helping-hand", "friend-guard", "priority", "ko"]


def test_missing_required_final_stat_stays_unavailable_without_inference() -> None:
    context = build_deterministic_calculation_context(
        {"current_final_stats": [_final("self", "attack", 200)]},
        None,
        {"move_id": "tackle", "category": "physical", "power": 40},
    )
    assert context is not None
    assert context["damage_estimates"] == [{
        "attacker_side": "self", "defender_side": "opponent", "move": "tackle", "damage_class": "physical",
        "calculation_scope": "base_damage_stage_only", "excluded_modifiers": ["stab", "type-effectiveness", "critical-hit", "burn", "weather", "terrain", "screens", "item", "ability", "spread", "helping-hand", "friend-guard", "priority", "ko"],
        "power": 40, "level": 50, "offensive_stat": 200, "calculation_status": "unavailable", "reason": "missing_defensive_stat",
    }]
