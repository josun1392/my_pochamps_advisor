"""Closed canonical owner for Counter and Mirror Coat."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-recent-damage-retaliation-family-v1"
_MOVES = {
    "counter": {"move_id": "counter", "type": "fighting", "category": "physical", "accuracy": 100, "priority": -5, "contact": True, "qualifying_category": "physical"},
    "mirror-coat": {"move_id": "mirror-coat", "type": "psychic", "category": "special", "accuracy": 100, "priority": -5, "contact": False, "qualifying_category": "special"},
}

def resolve_canonical_recent_damage_retaliation_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id:
        return {**base, "status": "incomplete", "reason": "canonical_move_identity_unknown"}
    effect = _MOVES.get(move_id)
    if effect is None: return {**base, "status": "unsupported", "reason": "move_not_in_recent_damage_retaliation_catalog"}
    if not isinstance(move, Mapping) or any(move.get(k) != v for k, v in effect.items() if k in move):
        return {**base, "status": "rejected", "reason": "catalog_metadata_mismatch"}
    return {**base, "status": "resolved", "effect": {**effect, "family": "recent_damage_multiplier", "multiplier": {"numerator": 2, "denominator": 1}, "zero_loss_damage": 1}, "provenance": "canonical-maintained-recent-damage-retaliation-family-v1"}
