from __future__ import annotations

import pytest

from llm.advisor_direct_mechanics import (
    _defensive_stat_source,
    _offensive_stat_source,
    _relevant_stage_context,
)


def _stage(side: str, stat: str, stage: object, **extra: object) -> dict[str, object]:
    return {
        "side": side,
        "stat": stat,
        "stage": stage,
        "status": "user_confirmed",
        "source": "user_confirmed_current_stat_stage",
        "confidence": "known",
        "slot_index": 0 if side == "self" else 1,
        "provenance": {
            "side": side,
            "slot_index": 0 if side == "self" else 1,
            "pokemon_id": "garchomp" if side == "self" else "tyranitar",
            "session_id": "s",
            "source": "user_confirmed_current_stat_stage",
            "trust": "user_confirmed_current",
        },
        **extra,
    }


def _context(*rows: dict[str, object]) -> dict[str, object]:
    return {"stat_stage_context": {"current_stages": list(rows)}}


def test_transported_attack_stage_unwraps_only_known_wrapper_fields_and_exposes_defender_stage() -> None:
    result = _relevant_stage_context(
        current=_context(_stage("self", "attack", 0)),
        category="physical",
    )

    assert result["unsupported_reason"] is None
    assert result["applied"] is False
    assert result["missing_inputs"] == ["defender.defense_stage"]


def test_transported_attack_and_defense_stages_resolve_normally() -> None:
    result = _relevant_stage_context(
        current=_context(
            _stage("self", "attack", 0),
            _stage("opponent", "defense", 0),
        ),
        category="physical",
    )

    assert result["unsupported_reason"] is None
    assert result["missing_inputs"] == []
    assert result["applied"] is True
    assert result["offensive_stage_value"] == 0
    assert result["defensive_stage_value"] == 0


@pytest.mark.parametrize(
    "row",
    [
        _stage("wrong", "attack", 0),
        _stage("self", "not-a-stat", 0),
        _stage("self", "attack", "0"),
        _stage("self", "attack", 7),
        {**_stage("self", "attack", 0), "status": "unknown"},
        {**_stage("self", "attack", 0), "source": "wrong_source"},
        _stage("self", "attack", 0, value=100),
        _stage("self", "attack", 0, unexpected_field="still-must-reject"),
    ],
)
def test_malformed_semantic_rows_remain_fail_closed(row: dict[str, object]) -> None:
    result = _relevant_stage_context(current=_context(row), category="physical")

    assert result["unsupported_reason"] == "stat_stage_context"
    assert result["missing_inputs"] == []


def test_duplicate_side_stat_remains_unsupported() -> None:
    result = _relevant_stage_context(
        current=_context(
            _stage("self", "attack", 0),
            _stage("self", "attack", 1),
        ),
        category="physical",
    )

    assert result["unsupported_reason"] == "stat_stage_context"


@pytest.mark.parametrize(
    ("move_id", "category", "rows", "offensive_stat", "defensive_stat"),
    [
        (
            "body-press",
            "physical",
            (_stage("self", "defense", 0), _stage("opponent", "defense", 0)),
            "defense",
            "defense",
        ),
        (
            "foul-play",
            "physical",
            (_stage("opponent", "attack", 0), _stage("opponent", "defense", 0)),
            "attack",
            "defense",
        ),
        (
            "psyshock",
            "special",
            (_stage("self", "special-attack", 0), _stage("opponent", "defense", 0)),
            "special-attack",
            "defense",
        ),
    ],
)
def test_transported_rows_preserve_alternate_stat_families(
    move_id: str,
    category: str,
    rows: tuple[dict[str, object], ...],
    offensive_stat: str,
    defensive_stat: str,
) -> None:
    offensive_source = _offensive_stat_source(move_id=move_id, category=category)
    defensive_source = _defensive_stat_source(move_id=move_id, category=category)
    result = _relevant_stage_context(
        current=_context(*rows),
        category=category,
        offensive_source=offensive_source,
        defensive_source=defensive_source,
    )

    assert result["unsupported_reason"] is None
    assert result["missing_inputs"] == []
    assert result["applied"] is True
    assert result["evidence"]["offensive_stage_stat"] == offensive_stat
    assert result["evidence"]["defensive_stage_stat"] == defensive_stat
