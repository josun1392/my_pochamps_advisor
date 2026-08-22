"""Materialize one trusted observed drag-out request into existing authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_forced_switch_request import materialize_forced_switch_request
from llm.advisor_ice_body_end_of_turn import _owners
from llm.advisor_transition_preview import fingerprint_transition_preview_state


OBSERVED_REQUEST_SCHEMA_VERSION = "observed-forced-switch-request-v1"
_OBSERVED_PROVENANCE = "trusted_observed_forced_switch_request_v1"
_REQUEST_PROVENANCE = "trusted_forced_switch_request_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_OBSERVED_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "target_owner",
    "request_kind", "result", "provenance",
})


def materialize_observed_forced_switch_request(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str, observed_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Purely validate observed `drag_out_requested` evidence into v1 request."""
    owners = _owners(branch_state)
    if owners is None or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_forced_switch_branch")
    if not _valid_observation(observed_request, source_branch_fingerprint, owners):
        return _result("rejected", "invalid_observed_forced_switch_request")
    request = {
        "schema_version": "forced-switch-request-v1",
        "session_id": observed_request["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "target_owner": deepcopy(dict(observed_request["target_owner"])),
        "request_kind": "drag_out",
        "provenance": _REQUEST_PROVENANCE,
    }
    resolved = materialize_forced_switch_request(
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        observed_request=request,
    )
    if resolved.get("status") != "resolved":
        return resolved
    return {
        "status": "resolved",
        "observed_forced_switch_request": deepcopy(dict(observed_request)),
        "forced_switch_request": resolved["forced_switch_request"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "target_owner": deepcopy(dict(observed_request["target_owner"])),
        "provenance": _OBSERVED_PROVENANCE,
        "materialization": "pure_idempotent",
    }


def _valid_observation(value: Any, fingerprint: str, owners: Mapping[str, Mapping[str, Any]]) -> bool:
    if not isinstance(value, Mapping) or set(value) != _OBSERVED_KEYS:
        return False
    target = value.get("target_owner")
    return (
        _exact_owner(target)
        and value.get("schema_version") == OBSERVED_REQUEST_SCHEMA_VERSION
        and value.get("session_id") == target.get("session_id") == owners[target["side"]].get("session_id")
        and value.get("source_branch_fingerprint") == fingerprint
        and value.get("request_kind") == "drag_out"
        and value.get("result") == "drag_out_requested"
        and value.get("provenance") == _OBSERVED_PROVENANCE
        and dict(target) == dict(owners[target["side"]])
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
