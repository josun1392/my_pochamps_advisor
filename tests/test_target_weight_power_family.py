from __future__ import annotations

import pytest

from advisor.canonical_target_weight_power_family import resolve_canonical_target_weight_power_move
from llm.advisor_battle_state_context import (
    build_target_weight_power_assessment,
    resolve_registered_dynamic_move,
)


@pytest.mark.parametrize(("move_id", "category", "type_"), [
    ("low-kick", "physical", "fighting"),
    ("grass-knot", "special", "grass"),
])
def test_catalog_metadata_is_exact(move_id: str, category: str, type_: str) -> None:
    result = resolve_canonical_target_weight_power_move(move={"move_id": move_id})
    assert result["status"] == "resolved"
    assert result["effect"] == {
        "move_id": move_id, "type": type_, "category": category, "accuracy": 100,
        "priority": 0, "contact": True, "protection_blockable": True,
        "family": "target_weight_power",
    }


@pytest.mark.parametrize(("weight", "power"), [
    (1, 20), (99, 20), (100, 40), (249, 40), (250, 60), (499, 60),
    (500, 80), (999, 80), (1000, 100), (1999, 100), (2000, 120), (2001, 120),
])
@pytest.mark.parametrize("move_id", ["low-kick", "grass-knot"])
def test_exact_hectogram_boundaries(move_id: str, weight: int, power: int) -> None:
    result = build_target_weight_power_assessment({"move_id": move_id}, {"opponent_weight": weight})
    assert result["status"] == "resolved"
    assert result["target_weight"] == weight
    assert result["effective_power"] == power


def test_target_weight_requires_no_attacker_weight_and_fails_closed_when_missing_or_invalid() -> None:
    assert build_target_weight_power_assessment({"move_id": "low-kick"}, {"opponent_weight": 2000})["effective_power"] == 120
    assert build_target_weight_power_assessment({"move_id": "low-kick"}, None)["reason"] == "missing_target_weight"
    assert build_target_weight_power_assessment({"move_id": "grass-knot"}, {"opponent_weight": 10.0})["reason"] == "invalid_target_weight"


def test_registry_uses_distinct_target_weight_family_and_preserves_formula_override() -> None:
    result = resolve_registered_dynamic_move(
        {"move_id": "grass-knot"}, limited_context_enabled=True, weight_context={"opponent_weight": 1000},
    )
    assert result == {
        "assessment_key": "target_weight_power_assessment",
        "assessment_payload": {
            "move": "grass-knot", "scope": "explicit-target-weight-based-move-power-only",
            "family": "target_weight_power", "rule": "target-absolute-weight-bracket",
            "target_weight": 1000, "weight_unit": "hectogram", "threshold_bucket": "100kg_to_under_200kg",
            "effective_power": 100, "status": "resolved",
        },
        "effective_power_override": 100,
    }
