"""Maintained, deliberately small catalog for plain self-healing moves."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "canonical-direct-heal-move-family-v1"
_CATALOG = {
    move_id: {"move_id": move_id, "category": "status", "target": "self", "priority": 0,
              "accuracy": None, "power": None, "consequence_family": "plain_half_max_hp_self_heal"}
    for move_id in ("recover", "slack-off", "soft-boiled")
}


def resolve_canonical_direct_heal_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id:
        return {**base, "status": "incomplete", "reason": "canonical_move_identity_unknown"}
    row = _CATALOG.get(move_id)
    if row is None:
        return {**base, "status": "unsupported", "reason": "move_not_in_direct_heal_move_catalog"}
    if not isinstance(move, Mapping):
        return {**base, "status": "incomplete", "reason": "canonical_move_metadata_unknown"}
    for key in ("category", "target", "priority", "accuracy", "power"):
        if move.get(key) != row[key]:
            return {**base, "status": "rejected", "reason": f"catalog_metadata_{key}_mismatch"}
    return {**base, "status": "resolved", "effect": deepcopy(row),
            "provenance": "canonical-maintained-direct-heal-family-v1"}
