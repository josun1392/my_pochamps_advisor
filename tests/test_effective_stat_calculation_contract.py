from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_effective_stat_inputs, calculate_stage_adjusted_stat


def _final(*entries: dict[str, object]) -> dict[str, object]:
    return {"current_final_stats": list(entries)}


def _entry(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


@pytest.mark.parametrize(("value", "stage", "expected"), [(167, 0, 167), (167, 2, 334), (201, -1, 134), (1, -6, 0), (167, 6, 668)])
def test_stage_adjusted_stat_uses_floor_standard_stage_multiplier(value: int, stage: int, expected: int) -> None:
    assert calculate_stage_adjusted_stat(value, stage) == expected


def test_effective_stats_use_only_confirmed_final_stat_and_current_stage() -> None:
    context = build_effective_stat_inputs(
        _final(_entry("self", "attack", 205), _entry("self", "hp", 301)),
        {"current_stages": [
            {"side": "self", "stat": "attack", "stage": -1, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"},
        ]},
    )
    assert context is not None
    assert context["effective_stats"] == [{"side": "self", "stat": "attack", "base_final_value": 205, "stage": -1, "effective_value": 136, "calculation_status": "resolved"}]
    assert context["calculation_scope"] == "final_stat_plus_stage_only"
    assert context["excluded_modifiers"] == ["priority", "item", "ability", "weather", "terrain", "tailwind", "trick-room", "rng"]


def test_stage_without_final_stat_is_not_calculated_and_final_stat_defaults_to_stage_zero() -> None:
    context = build_effective_stat_inputs(
        _final(_entry("self", "speed", 167)),
        {"current_stages": [{"side": "opponent", "stat": "speed", "stage": 6, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]},
    )
    assert context is not None
    assert context["effective_stats"][0]["stage"] == 0
    assert context["effective_stats"][0]["effective_value"] == 167
