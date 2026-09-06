"""Closed canonical owner for same-turn recent-damage retaliation."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-recent-damage-retaliation-family-v1"
_MOVES = {
    "counter": {"move_id": "counter", "type": "fighting", "category": "physical", "accuracy": 100, "priority": -5, "contact": True, "qualifying_category_policy": "physical_only", "multiplier": {"numerator": 2, "denominator": 1}, "rounding": "exact_integer"},
    "mirror-coat": {"move_id": "mirror-coat", "type": "psychic", "category": "special", "accuracy": 100, "priority": -5, "contact": False, "qualifying_category_policy": "special_only", "multiplier": {"numerator": 2, "denominator": 1}, "rounding": "exact_integer"},
    "comeuppance": {"move_id": "comeuppance", "type": "dark", "category": "physical", "accuracy": 100, "priority": 0, "contact": True, "qualifying_category_policy": "physical_or_special", "multiplier": {"numerator": 3, "denominator": 2}, "rounding": "floor"},
    "metal-burst": {"move_id": "metal-burst", "type": "steel", "category": "physical", "accuracy": 100, "priority": 0, "contact": False, "qualifying_category_policy": "physical_or_special", "multiplier": {"numerator": 3, "denominator": 2}, "rounding": "floor"},
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
    return {**base, "status": "resolved", "effect": {**effect, "family": "recent_damage_multiplier", "zero_loss_damage": 1}, "provenance": "canonical-maintained-recent-damage-retaliation-family-v2"}
