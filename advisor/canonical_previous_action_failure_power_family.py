"""Closed metadata and qualification policy for Stomping Tantrum."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-previous-action-failure-power-family-v1"
_MOVE = {"move_id": "stomping-tantrum", "type": "ground", "category": "physical", "power": 75, "accuracy": 100, "priority": 0, "contact": True}
# Protection is deliberately false: it prevents the target, not the user's move
# from failing for this single-target rule.  The remaining classes are the
# exact result vocabulary accepted by the reducer-owned history.
QUALIFYING_FAILURE_RESULTS = frozenset({"accuracy_miss", "type_or_ability_immunity", "move_specific_failure", "full_paralysis", "flinch", "sleep", "freeze"})
NONQUALIFYING_RESULTS = frozenset({"success", "protection_block", "recharge", "sky_drop"})

def resolve_canonical_previous_action_failure_power_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if move_id != "stomping-tantrum": return {**base, "status": "unsupported", "reason": "move_not_in_previous_action_failure_power_catalog"}
    if not isinstance(move, Mapping) or any(move.get(k) != v for k, v in _MOVE.items() if k in move): return {**base, "status": "rejected", "reason": "catalog_metadata_mismatch"}
    return {**base, "status": "resolved", "effect": {**_MOVE, "family": "previous_action_failure_power", "boosted_power": 150, "condition": "same_active_pokemon_previous_action_qualifies_as_failure"}, "provenance": "canonical-maintained-previous-action-failure-power-family-v1"}

def qualifies_as_previous_move_failure(result_class: Any) -> bool | None:
    if result_class in QUALIFYING_FAILURE_RESULTS: return True
    if result_class in NONQUALIFYING_RESULTS: return False
    return None
