"""Map trusted observed Roar/Whirlwind applications into drag-out requests."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_observed_forced_switch_request import materialize_observed_forced_switch_request
from llm.advisor_transition_preview import fingerprint_transition_preview_state


OBSERVED_SOURCE_SCHEMA_VERSION = "observed-forced-switch-source-application-v1"
_OBSERVED_SOURCE_PROVENANCE = "trusted_observed_forced_switch_source_application_v1"
_OBSERVED_REQUEST_PROVENANCE = "trusted_observed_forced_switch_request_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_REQUIRED = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "user",
    "target_owner", "move_id", "applied_effect", "result", "provenance",
})
_SUPPORTED = {
    "roar": "drag_out",
    "whirlwind": "drag_out",
}


def materialize_observed_forced_switch_source_application(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_source_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Purely materialize one exact observed Roar/Whirlwind application.

    The observation already establishes that the phazing effect applied.  This
    seam deliberately neither resolves the move nor executes the switch; it
    only adapts the evidence into the established drag-out request authority.
    """
    active = branch_state.get("active") if isinstance(branch_state, Mapping) else None
    if not isinstance(active, Mapping) or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_forced_switch_source_branch")
    if not _valid_source_result(observed_source_result, source_branch_fingerprint, active):
        return _result("rejected", "invalid_observed_forced_switch_source_application")

    target = observed_source_result["target_owner"]
    observed_request = {
        "schema_version": "observed-forced-switch-request-v1",
        "session_id": target["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "target_owner": deepcopy(dict(target)),
        "request_kind": "drag_out",
        "result": "drag_out_requested",
        "provenance": _OBSERVED_REQUEST_PROVENANCE,
    }
    materialized = materialize_observed_forced_switch_request(
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        observed_request=observed_request,
    )
    if materialized.get("status") != "resolved":
        return materialized
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "observed_forced_switch_source_application": deepcopy(dict(observed_source_result)),
        "observed_forced_switch_request": materialized["observed_forced_switch_request"],
        "forced_switch_request": materialized["forced_switch_request"],
        "trace": {
            "event": "observed_forced_switch_source_materialized",
            "move_id": observed_source_result["move_id"],
            "applied_effect": "drag_out",
            "provenance": _OBSERVED_SOURCE_PROVENANCE,
        },
        "materialization": "pure_idempotent",
    }


def _valid_source_result(value: Any, fingerprint: str, active: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or set(value) != _REQUIRED:
        return False
    user, target = value.get("user"), value.get("target_owner")
    if not _exact_owner(user) or not _exact_owner(target):
        return False
    move_id = value.get("move_id")
    return (
        value.get("schema_version") == OBSERVED_SOURCE_SCHEMA_VERSION
        and value.get("result") == "applied"
        and value.get("provenance") == _OBSERVED_SOURCE_PROVENANCE
        and move_id in _SUPPORTED
        and value.get("applied_effect") == _SUPPORTED[move_id]
        and value.get("source_branch_fingerprint") == fingerprint
        and value.get("session_id") == user["session_id"] == target["session_id"]
        and user["side"] != target["side"]
        and _current_owner(active, user)
        and _current_owner(active, target)
        and not active[user["side"]].get("fainted")
        and not active[target["side"]].get("fainted")
    )


def _exact_owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value["slot_index"], bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _current_owner(active: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    current = active.get(owner["side"])
    return isinstance(current, Mapping) and dict(owner) == {key: current.get(key) for key in _OWNER_KEYS}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
