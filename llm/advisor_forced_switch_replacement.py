"""Bounded self-side forced replacement authority; no selection policy."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_forced_switch_request import materialize_forced_switch_request
from llm.advisor_transition_preview import fingerprint_transition_preview_state


OBSERVED_SCHEMA = "observed-forced-replacement-result-v1"
AUTHORITY_SCHEMA = "forced-switch-replacement-authority-v1"
OBSERVED_PROVENANCE = "trusted_observed_forced_replacement_result_v1"
AUTHORITY_PROVENANCE = "trusted_forced_switch_replacement_authority_v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_FAMILIES = ("aqua_ring", "ingrain", "leech_seed")
_OBSERVED_KEYS = frozenset({
    "schema_version", "session_id", "source_branch_fingerprint", "outgoing_owner",
    "incoming_authority", "outgoing_bench_authority", "entry_authority",
    "replacement_status", "provenance",
})


def materialize_observed_forced_replacement_result(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    observed_replacement: Mapping[str, Any],
) -> dict[str, Any]:
    """Purely validate one observed, already-resolved self-side replacement."""
    if fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_observed_replacement_branch")
    if not _valid_observation(branch_state, source_branch_fingerprint, observed_replacement):
        return _result("rejected", "invalid_observed_forced_replacement_result")
    return {
        "status": "resolved",
        "observed_forced_replacement_result": deepcopy(dict(observed_replacement)),
        "source_branch_fingerprint": source_branch_fingerprint,
        "outgoing_owner": deepcopy(dict(observed_replacement["outgoing_owner"])),
        "incoming_owner": deepcopy(dict(observed_replacement["incoming_authority"]["owner"])),
        "materialization": "pure_idempotent",
        "provenance": OBSERVED_PROVENANCE,
    }


def materialize_forced_switch_replacement_authority(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str,
    forced_switch_request: Mapping[str, Any], cancellation_decision: Mapping[str, Any],
    observed_replacement: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one trusted observed replacement to an allowed F0 drag-out request."""
    observed = materialize_observed_forced_replacement_result(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        observed_replacement=observed_replacement,
    )
    if observed.get("status") != "resolved":
        return observed
    request = materialize_forced_switch_request(
        branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint,
        observed_request=forced_switch_request,
    )
    if request.get("status") != "resolved":
        return request
    outgoing = observed_replacement["outgoing_owner"]
    if (
        forced_switch_request.get("target_owner") != outgoing
        or not _allowed_decision(cancellation_decision, source_branch_fingerprint, forced_switch_request, outgoing)
    ):
        return _result("rejected", "incompatible_forced_switch_cancellation_decision")
    return {
        "status": "resolved",
        "schema_version": AUTHORITY_SCHEMA,
        "session_id": outgoing["session_id"],
        "source_branch_fingerprint": source_branch_fingerprint,
        "outgoing_owner": deepcopy(dict(outgoing)),
        "incoming_authority": deepcopy(dict(observed_replacement["incoming_authority"])),
        "outgoing_bench_authority": deepcopy(dict(observed_replacement["outgoing_bench_authority"])),
        "entry_authority": deepcopy(dict(observed_replacement["entry_authority"])),
        "provenance": AUTHORITY_PROVENANCE,
    }


def _valid_observation(branch: Mapping[str, Any], fingerprint: str, value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != _OBSERVED_KEYS:
        return False
    active = branch.get("active") if isinstance(branch, Mapping) else None
    outgoing = value.get("outgoing_owner")
    incoming = value.get("incoming_authority")
    if not isinstance(active, Mapping) or not _owner(outgoing) or not isinstance(incoming, Mapping):
        return False
    owner = incoming.get("owner")
    if (
        value.get("schema_version") != OBSERVED_SCHEMA
        or value.get("session_id") != outgoing.get("session_id")
        or value.get("source_branch_fingerprint") != fingerprint
        or value.get("replacement_status") != "replacement_resolved"
        or value.get("provenance") != OBSERVED_PROVENANCE
        or not isinstance(active.get("self"), Mapping)
        or {key: active["self"].get(key) for key in _OWNER_KEYS} != dict(outgoing)
        or not _owner(owner)
        or owner.get("session_id") != outgoing.get("session_id")
        or owner.get("side") != "self"
        or dict(owner) == dict(outgoing)
        or not _valid_incoming(incoming)
        or not _valid_bench(value.get("outgoing_bench_authority"), outgoing, active["self"])
        or not _available_in_roster(branch, owner)
        or not _valid_entry_authority(value.get("entry_authority"), owner, outgoing["session_id"])
    ):
        return False
    return True


def _valid_incoming(value: Mapping[str, Any]) -> bool:
    hp, fainted, current, persistent = value.get("hp_authority"), value.get("fainted_authority"), value.get("current_state"), value.get("persistent_effect_states")
    if value.get("provenance") != "identity_bound_incoming_current_state_v1" or not _known_hp(hp):
        return False
    if not isinstance(fainted, Mapping) or fainted.get("status") != "known" or fainted.get("value") is not False:
        return False
    if not isinstance(current, Mapping) or current.get("current_state_session_id") != value["owner"]["session_id"]:
        return False
    if not isinstance(persistent, Mapping) or set(persistent) != set(_FAMILIES):
        return False
    for family in _FAMILIES:
        row = persistent[family]
        if not isinstance(row, Mapping) or row.get("state") not in {"known_active", "known_inactive", "unknown"}:
            return False
        if family == "leech_seed" and row["state"] == "known_active" and not _source_slot(row.get("source_slot"), value["owner"]["session_id"]):
            return False
        if family != "leech_seed" and "source_slot" in row:
            return False
    return True


def _valid_bench(value: Any, owner: Mapping[str, Any], active: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or set(value) != {"owner", "hp_authority", "fainted_authority", "retained_current_state", "provenance"}:
        return False
    hp, fainted = value.get("hp_authority"), value.get("fainted_authority")
    return (
        value.get("owner") == dict(owner) and value.get("provenance") == "trusted_forced_switch_outgoing_bench_v1"
        and _known_hp(hp) and hp["current_hp"] == active.get("current_hp") and hp["maximum_hp"] == active.get("max_hp")
        and isinstance(fainted, Mapping) and fainted.get("status") == "known" and fainted.get("value") == active.get("fainted")
        and isinstance(value.get("retained_current_state"), Mapping)
    )


def _available_in_roster(branch: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    current = branch.get("current_state") if isinstance(branch, Mapping) else None
    roster = current.get("self_roster_mechanics_context") if isinstance(current, Mapping) else None
    rows = roster.get("entries") if isinstance(roster, Mapping) else None
    match = next((row for row in rows if isinstance(row, Mapping) and all(row.get(key) == owner.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id"))), None) if isinstance(rows, list) else None
    return isinstance(match, Mapping) and isinstance(match.get("fainted_authority"), Mapping) and match["fainted_authority"].get("status") == "known" and match["fainted_authority"].get("value") is False


def _valid_entry_authority(value: Any, incoming: Mapping[str, Any], session: str) -> bool:
    return isinstance(value, Mapping) and set(value) == {"hazards", "target_roster_mechanics", "intimidate_authority", "download_authority", "field_state_context", "provenance"} and value.get("provenance") == "trusted_forced_switch_entry_authority_v1" and isinstance(value.get("hazards"), Mapping) and isinstance(value.get("target_roster_mechanics"), Mapping) and value["target_roster_mechanics"].get("session_id") == session and value["target_roster_mechanics"].get("side") == "self" and value["target_roster_mechanics"].get("slot_index") == incoming.get("slot_index") and value["target_roster_mechanics"].get("pokemon_id") == incoming.get("pokemon_id")


def _allowed_decision(value: Any, fingerprint: str, request: Mapping[str, Any], outgoing: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("schema_version") == "forced-switch-cancellation-decision-v1" and value.get("source_branch_fingerprint") == fingerprint and value.get("forced_switch_request") == dict(request) and value.get("target_owner") == dict(outgoing) and value.get("decision") == "allowed_to_proceed" and value.get("provenance") == "trusted_canonical_showdown_ingrain_drag_out"


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _known_hp(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("current_hp"), int) and not isinstance(value["current_hp"], bool) and isinstance(value.get("maximum_hp"), int) and not isinstance(value["maximum_hp"], bool) and value["maximum_hp"] > 0 and 0 < value["current_hp"] <= value["maximum_hp"]


def _source_slot(value: Any, session: str) -> bool:
    return isinstance(value, Mapping) and set(value) == {"session_id", "side", "slot_index"} and value.get("session_id") == session and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
