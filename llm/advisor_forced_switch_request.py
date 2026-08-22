"""Bounded forced-removal request and Ingrain cancellation authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _owners
from llm.advisor_persistent_effect_authority import persistent_effect_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state


REQUEST_SCHEMA_VERSION = "forced-switch-request-v1"
DECISION_SCHEMA_VERSION = "forced-switch-cancellation-decision-v1"
_REQUEST_PROVENANCE = "trusted_forced_switch_request_v1"
_DECISION_PROVENANCE = "trusted_canonical_showdown_ingrain_drag_out"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_REQUEST_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "target_owner",
    "request_kind", "provenance",
})


def materialize_forced_switch_request(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str, observed_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one exact trusted `drag_out` request without executing it."""
    owners = _owners(branch_state)
    if owners is None or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_forced_switch_branch")
    if not _valid_request(observed_request, source_branch_fingerprint, owners):
        return _result("rejected", "stale_or_invalid_forced_switch_request")
    return {
        "status": "resolved",
        "forced_switch_request": deepcopy(dict(observed_request)),
        "source_branch_fingerprint": source_branch_fingerprint,
        "target_owner": deepcopy(dict(observed_request["target_owner"])),
        "boundary": {"phase": "forced_switch_request"},
    }


def decide_forced_switch_cancellation(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str, forced_switch_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve only Ingrain's `onDragOut` cancellation for one exact request."""
    request = materialize_forced_switch_request(
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        observed_request=forced_switch_request,
    )
    if request.get("status") != "resolved":
        return request
    owners = _owners(branch_state)
    assert owners is not None  # validated above
    target = forced_switch_request["target_owner"]
    side = target["side"]
    row = persistent_effect_state(branch_state, "ingrain", side, target)
    if row is None:
        return _result("rejected", "stale_or_invalid_ingrain_forced_switch_authority")
    if row["state"] == "unknown":
        return _result("incomplete", "ingrain_persistent_effect_unknown")
    outcome = "cancelled" if row["state"] == "known_active" else "allowed_to_proceed"
    return {
        "status": "resolved",
        "schema_version": DECISION_SCHEMA_VERSION,
        "session_id": target["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "forced_switch_request": deepcopy(dict(forced_switch_request)),
        "target_owner": deepcopy(dict(target)),
        "ingrain_state": row["state"],
        "decision": outcome,
        "cancellation_source": "ingrain_on_drag_out" if outcome == "cancelled" else None,
        "provenance": _DECISION_PROVENANCE,
        "replacement_execution": "out_of_scope",
        "branch_mutation": "none",
    }


def _valid_request(request: Any, fingerprint: str, owners: Mapping[str, Mapping[str, Any]]) -> bool:
    if not isinstance(request, Mapping) or set(request) != _REQUEST_KEYS:
        return False
    target = request.get("target_owner")
    if not _exact_owner(target):
        return False
    side = target["side"]
    return (
        request.get("schema_version") == REQUEST_SCHEMA_VERSION
        and request.get("session_id") == owners[side]["session_id"]
        and request.get("source_branch_fingerprint") == fingerprint
        and request.get("request_kind") == "drag_out"
        and request.get("provenance") == _REQUEST_PROVENANCE
        and dict(target) == dict(owners[side])
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


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
