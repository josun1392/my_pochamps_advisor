"""Trusted frozen cross-owner target order for Ingrain residual tier seven."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from llm.advisor_ice_body_end_of_turn import _owners
from llm.advisor_transition_preview import fingerprint_transition_preview_state

_PROVENANCE = "trusted_canonical_showdown_ingrain_residual_target_order"
_REQUIRED = {"schema_version", "status", "session_id", "event_family", "source_branch_fingerprint", "ordered_active_owners", "provenance"}


def validate_ingrain_target_order(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, material_owners: Sequence[Mapping[str, Any]], projection: Mapping[str, Any] | None) -> dict[str, Any]:
    owners = _owners(branch_state)
    if owners is None or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_pre_ingrain_branch")
    if not isinstance(projection, Mapping) or set(projection) != _REQUIRED or projection.get("schema_version") != "detached-ingrain-target-order-v1" or projection.get("status") != "known" or projection.get("event_family") != "ResidualIngrainTier7" or projection.get("provenance") != _PROVENANCE:
        return _result("incomplete", "cross_owner_ingrain_order_unrepresented")
    if projection.get("session_id") != owners["self"]["session_id"] or projection.get("source_branch_fingerprint") != source_branch_fingerprint:
        return _result("rejected", "stale_or_foreign_ingrain_target_order")
    rows = projection.get("ordered_active_owners")
    if not isinstance(rows, list) or len(rows) != len(material_owners) or any(not isinstance(row, Mapping) for row in rows):
        return _result("incomplete", "cross_owner_ingrain_order_unrepresented")
    normalized = [{key: row.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")} for row in rows]
    key = lambda values: {(x["session_id"], x["side"], x["slot_index"], x["pokemon_id"]) for x in values}
    if any(row not in material_owners for row in normalized) or len(key(normalized)) != len(normalized) or key(normalized) != key(material_owners):
        return _result("rejected", "invalid_ingrain_target_order_owners")
    return {"status": "resolved", "frozen_ingrain_plan": {"session_id": projection["session_id"], "event_family": "ResidualIngrainTier7", "source_branch_fingerprint": source_branch_fingerprint, "ordered_active_owners": deepcopy(normalized), "provenance": _PROVENANCE}}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
