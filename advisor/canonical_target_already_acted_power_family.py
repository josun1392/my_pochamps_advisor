"""Closed canonical metadata for Payback's target-already-acted power rule."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-target-already-acted-power-family-v1"
_PAYBACK = {"move_id": "payback", "type": "dark", "category": "physical", "power": 50, "accuracy": 100, "priority": 0, "contact": True}

def resolve_canonical_target_already_acted_power_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None; base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if move_id != "payback": return {**base, "status": "unsupported", "reason": "move_not_in_target_already_acted_power_catalog"}
    if not isinstance(move, Mapping) or any(move.get(key) != value for key, value in _PAYBACK.items() if key in move): return {**base, "status": "rejected", "reason": "catalog_metadata_mismatch"}
    return {**base, "status": "resolved", "effect": {**_PAYBACK, "family": "target_already_acted_same_turn_power", "boosted_power": 100, "condition": "target_completed_action_before_payback_execution"}, "provenance": "canonical-maintained-target-already-acted-power-family-v1"}
