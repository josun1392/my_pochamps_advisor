from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import (
    build_current_stat_stage_context_from_confirmations,
    normalize_user_confirmed_current_stat_stage,
)


def _stage(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "side": "self", "stat": "attack", "stage": -1,
        "status": "user_confirmed", "source": "user_confirmed_current_stat_stage",
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    ("stat", "canonical"),
    [("attack", "attack"), ("atk", "attack"), ("def", "defense"), ("spa", "special-attack"), ("sp-atk", "special-attack"), ("sp-def", "special-defense"), ("speed", "speed"), ("accuracy", "accuracy"), ("evasion", "evasion")],
)
def test_normalizes_supported_current_stat_stage_ids(stat: str, canonical: str) -> None:
    assert normalize_user_confirmed_current_stat_stage(_stage(stat=stat))["stat"] == canonical


@pytest.mark.parametrize("stage", [-7, 7, 1.5, "max", "unknown", True])
def test_rejects_invalid_stage_values(stage: object) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_stat_stage(_stage(stage=stage))


@pytest.mark.parametrize(
    "field",
    ["stage_changed_this_turn", "stage_change_source", "ability_triggered", "exact_stat_value", "effective_stat", "exact_damage", "final_speed_order", "rng_roll", "post_turn_stage"],
)
def test_rejects_forbidden_current_stage_fields_recursively(field: str) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_stat_stage(_stage(**{field: {"nested": True}}))


def test_context_omits_invalid_entries_and_replaces_same_side_stat() -> None:
    context = build_current_stat_stage_context_from_confirmations([
        _stage(), _stage(stage=2), _stage(side="opponent", stat="speed", stage=6), _stage(stat="speed", stage=8),
    ])
    assert context == {"current_stages": [
        {**_stage(stage=2), "confidence": "known"},
        {**_stage(side="opponent", stat="speed", stage=6), "confidence": "known"},
    ]}
