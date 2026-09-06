"""Read-only, D0-bound authority for field-based held-item suppression."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-item-suppression-field-authority-v1"
MAGIC_ROOM_FIELD_ID = "magic-room"


def resolve_runtime_d0_item_suppression_field_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], field_id: str = MAGIC_ROOM_FIELD_ID,
) -> dict[str, Any]:
    """Resolve one canonical item's field-suppression gate without mutation.

    Only a reducer-owned, user-confirmed Magic Room observation may establish
    either active or known-absent.  Missing state intentionally remains
    incomplete: a model default is never field authority.
    """
    base = _base(strategy_d0, field_id)
    if base is None:
        return _result("rejected", "invalid_item_suppression_field_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    field = state.get("field") if isinstance(state, Mapping) else None
    if not isinstance(field, Mapping):
        return _result("incomplete", "item_suppression_field_unknown", base)
    state_value = field.get("magic_room_status")
    provenance = field.get("magic_room_status_provenance")
    if not _observed_magic_room(state_value, provenance):
        return _result("incomplete", "item_suppression_field_unknown", base)
    semantic_state = "active" if state_value == "active" else "known_absent"
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "state": semantic_state,
        "item_effects_suppressed": state_value == "active",
        "source_field_provenance": deepcopy(dict(provenance)),
        "provenance": "runtime_d0_reducer_owned_magic_room_item_suppression_v1",
    }


def _base(strategy_d0: Any, field_id: Any) -> dict[str, Any] | None:
    required = {"status", "schema_version", "session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner", "active_owners"}
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or strategy_d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not required <= set(strategy_d0):
        return None
    if field_id != MAGIC_ROOM_FIELD_ID or not isinstance(strategy_d0.get("session_id"), str) or not strategy_d0["session_id"] or not isinstance(strategy_d0.get("source_runtime_fingerprint"), str) or not strategy_d0["source_runtime_fingerprint"] or not isinstance(strategy_d0.get("strategy_preview_fingerprint"), str) or not strategy_d0["strategy_preview_fingerprint"]:
        return None
    return {
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(strategy_d0["decision_owner"]),
        "field_id": MAGIC_ROOM_FIELD_ID,
    }


def _observed_magic_room(value: Any, provenance: Any) -> bool:
    return (
        isinstance(value, str)
        and value in {"active", "inactive"}
        and isinstance(provenance, Mapping)
        and provenance.get("event_kind") == "magic_room_field_observed"
        and provenance.get("trust") == "user_confirmed_observation"
        and isinstance(provenance.get("source_observation_id"), str)
        and bool(provenance["source_observation_id"])
        and isinstance(provenance.get("source_sequence"), int)
        and not isinstance(provenance["source_sequence"], bool)
        and provenance["source_sequence"] >= 1
    )


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "field_id": MAGIC_ROOM_FIELD_ID, "state": "unknown", "item_effects_suppressed": None, "reason": reason}
