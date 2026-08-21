"""Trusted frozen target-order authority for one detached Weather event."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _owners
from llm.advisor_transition_preview import fingerprint_transition_preview_state


_PROVENANCE = "trusted_canonical_showdown_weather_event_target_order"
_REQUIRED = {"schema_version", "status", "session_id", "event_family", "source_branch_fingerprint", "ordered_active_owners", "provenance"}


def validate_weather_event_target_order(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, projection: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a complete canonical Weather plan before its first mutation."""
    owners = _owners(branch_state)
    if owners is None or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_pre_weather_branch")
    if not isinstance(projection, Mapping) or set(projection) != _REQUIRED:
        return _result("incomplete", "cross_owner_weather_order_unrepresented")
    if projection.get("schema_version") != "detached-weather-event-target-order-v1" or projection.get("status") != "known" or projection.get("event_family") != "Weather" or projection.get("provenance") != _PROVENANCE:
        return _result("incomplete", "cross_owner_weather_order_unrepresented")
    if projection.get("session_id") != owners["self"]["session_id"] or projection.get("source_branch_fingerprint") != source_branch_fingerprint:
        return _result("rejected", "stale_or_foreign_weather_event_target_order")
    rows = projection.get("ordered_active_owners")
    expected = [owner for owner in owners.values() if not branch_state["active"][owner["side"]]["fainted"]]
    if not isinstance(rows, list) or len(rows) != len(expected) or any(not isinstance(row, Mapping) for row in rows):
        return _result("incomplete", "cross_owner_weather_order_unrepresented")
    normalized = [{key: row.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")} for row in rows]
    keys = lambda values: {(row["session_id"], row["side"], row["slot_index"], row["pokemon_id"]) for row in values}
    if any(row not in expected for row in normalized) or len(keys(normalized)) != len(normalized) or keys(normalized) != keys(expected):
        return _result("rejected", "invalid_weather_event_target_order_owners")
    return {"status": "resolved", "frozen_weather_event_plan": {"session_id": projection["session_id"], "event_family": "Weather", "source_branch_fingerprint": source_branch_fingerprint, "ordered_active_owners": deepcopy(normalized), "provenance": _PROVENANCE}}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
