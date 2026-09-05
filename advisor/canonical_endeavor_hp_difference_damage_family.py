"""Closed canonical owner for Endeavor's HP-difference damage rule."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-endeavor-hp-difference-damage-family-v1"
_MOVE = {"move_id": "endeavor", "type": "normal", "category": "physical", "accuracy": 100, "contact": True}


def resolve_canonical_endeavor_hp_difference_damage_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id:
        return {**base, "status": "incomplete", "reason": "canonical_move_identity_unknown"}
    if move_id != "endeavor":
        return {**base, "status": "unsupported", "reason": "move_not_in_endeavor_hp_difference_catalog"}
    if not isinstance(move, Mapping) or any(move.get(key) != value for key, value in _MOVE.items() if key in move):
        return {**base, "status": "rejected", "reason": "catalog_metadata_mismatch"}
    return {**base, "status": "resolved", "effect": {**_MOVE, "family": "hp_difference_damage", "relation": "target_hp_above_attacker_hp"}, "provenance": "canonical-maintained-endeavor-hp-difference-family-v1"}
