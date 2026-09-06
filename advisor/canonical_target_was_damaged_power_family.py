"""Closed canonical metadata for Assurance's target-hurt-this-turn power rule."""
from __future__ import annotations

from typing import Any, Mapping


SCHEMA_VERSION = "canonical-target-was-damaged-power-family-v1"
_ASSURANCE = {"move_id": "assurance", "type": "dark", "category": "physical", "power": 60, "accuracy": 100, "priority": 0, "contact": True}


def resolve_canonical_target_was_damaged_power_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if move_id != "assurance":
        return {**base, "status": "unsupported", "reason": "move_not_in_target_was_damaged_power_catalog"}
    if not isinstance(move, Mapping) or any(move.get(key) != value for key, value in _ASSURANCE.items() if key in move):
        return {**base, "status": "rejected", "reason": "catalog_metadata_mismatch"}
    return {**base, "status": "resolved", "effect": {**_ASSURANCE, "family": "target_was_damaged_same_turn_power", "boosted_power": 120, "condition": "target_took_positive_qualifying_pokemon_hp_damage_earlier_this_turn"}, "provenance": "canonical-maintained-target-was-damaged-power-family-v1"}
