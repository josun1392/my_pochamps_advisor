"""Closed catalog contract for Fling's supported core execution shell."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def resolve_canonical_fling_core_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    if move_id != "fling":
        return {"status": "unsupported", "move_id": move_id, "reason": "move_not_in_fling_core_catalog"}
    metadata = {
        "move_id": "fling", "type": "dark", "category": "physical", "power": 0,
        "power_kind": "held_item_fling_base_power", "accuracy": 100, "priority": 0,
        "contact": False, "protection_blockable": True, "family": "fling_core_item_power_and_throw",
    }
    return {"status": "resolved", "move_id": "fling", "metadata": deepcopy(metadata), "provenance": "canonical_fling_core_move_catalog_v1"}
