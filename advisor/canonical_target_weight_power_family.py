from __future__ import annotations

from typing import Any, Mapping


_MOVES = {
    "low-kick": {"type": "fighting", "category": "physical"},
    "grass-knot": {"type": "grass", "category": "special"},
}


def resolve_canonical_target_weight_power_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    if move_id not in _MOVES:
        return {"status": "unsupported", "move_id": move_id, "reason": "move_not_in_target_weight_power_catalog"}
    effect = {"move_id": move_id, "accuracy": 100, "priority": 0, "contact": True, "protection_blockable": True, "family": "target_weight_power", **_MOVES[move_id]}
    if not isinstance(move, Mapping) or any(move.get(key) != value for key, value in effect.items() if key in move):
        return {"status": "rejected", "move_id": move_id, "reason": "catalog_metadata_mismatch"}
    return {"status": "resolved", "move_id": move_id, "effect": effect, "provenance": "canonical-target-weight-power-family-v1"}
