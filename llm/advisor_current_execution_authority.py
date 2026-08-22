"""Frozen present-tense execution authority, separate from action selection.

Historical observed action results are deliberately never accepted here. A
fresh attack therefore remains ``observation_required`` in v1; identity-bound
incoming current state is the only execution-ready authority this adapter
currently carries.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence


_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SELECTION_SCHEMA = "deterministic-current-action-authority-v1"
_EXECUTION_SCHEMA = "deterministic-current-execution-authority-v1"
_CANDIDATE_SCHEMA = "deterministic-action-candidate-v1"


def freeze_current_execution_authority(
    *, selection_snapshot: Mapping[str, Any], switch_incoming: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Freeze strict, D0-bound execution records for a selection snapshot.

    Each supplied incoming authority must itself carry the D0 fingerprint. It
    remains the existing incoming-state shape, so the downstream materializer
    can consume it without a parallel switch-state model.
    """
    validated = _selection_d0(selection_snapshot)
    if validated is None:
        return _result("rejected", "invalid_selection_snapshot")
    owner, fingerprint, actions = validated
    incoming_by_id: dict[str, Mapping[str, Any]] = {}
    for incoming in switch_incoming:
        action_id = _matching_incoming_action_id(
            incoming=incoming, owner=owner, fingerprint=fingerprint, actions=actions,
        )
        if action_id is None or action_id in incoming_by_id:
            return _result("rejected", "foreign_or_stale_switch_execution_authority")
        incoming_by_id[action_id] = incoming

    records = []
    for action in actions:
        if action["action_type"] == "attack":
            records.append(_record(action["action_id"], "observation_required", "exact_damage_unknown"))
            continue
        incoming = incoming_by_id.get(action["action_id"])
        if incoming is None:
            records.append(_record(action["action_id"], "execution_incomplete", "incoming_state_unavailable"))
        else:
            records.append(_record(
                action["action_id"], "current_predictive_execution_authority",
                "incoming_current_state_bound", deepcopy(dict(incoming)),
            ))
    return {
        "status": "resolved",
        "schema_version": _EXECUTION_SCHEMA,
        "session_id": owner["session_id"],
        "decision_branch_fingerprint": fingerprint,
        "decision_owner": deepcopy(owner),
        "records": sorted(records, key=lambda record: record["action_id"]),
        "execution_coverage": {
            "current_predictive_execution_authority": sum(record["authority_class"] == "current_predictive_execution_authority" for record in records),
            "observation_required": sum(record["authority_class"] == "observation_required" for record in records),
            "execution_incomplete": sum(record["authority_class"] == "execution_incomplete" for record in records),
        },
    }


def enrich_discovered_candidates(
    *, selection_snapshot: Mapping[str, Any], execution_bundle: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Purely attach matching execution authority; never execute a candidate."""
    selection = _selection_d0(selection_snapshot)
    if selection is None or not _matching_execution_bundle(selection_snapshot, execution_bundle):
        return _result("rejected", "selection_execution_d0_mismatch")
    _, _, actions = selection
    action_ids = {action["action_id"] for action in actions}
    records = execution_bundle.get("records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return _result("rejected", "invalid_execution_bundle_records")
    lookup = {record.get("action_id"): record for record in records if isinstance(record, Mapping)}
    if len(lookup) != len(records) or set(lookup) != action_ids:
        return _result("rejected", "invalid_execution_bundle_records")

    enriched = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or candidate.get("schema_version") != _CANDIDATE_SCHEMA:
            return _result("rejected", "invalid_discovered_candidate")
        action_id = candidate.get("candidate_id")
        record = lookup.get(action_id)
        if action_id not in action_ids or not isinstance(record, Mapping):
            return _result("rejected", "foreign_discovered_candidate")
        row = deepcopy(dict(candidate))
        row["action_authority"] = deepcopy(record.get("authority"))
        row["execution_readiness"] = record.get("authority_class")
        row["execution_reason"] = record.get("reason")
        enriched.append(row)
    return {"status": "resolved", "candidates": enriched}


def _selection_d0(snapshot: Any) -> tuple[dict[str, Any], str, Sequence[Mapping[str, Any]]] | None:
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "resolved" or snapshot.get("schema_version") != _SELECTION_SCHEMA:
        return None
    owner = snapshot.get("decision_owner")
    fingerprint = snapshot.get("decision_branch_fingerprint")
    actions = snapshot.get("actions")
    if not _owner(owner) or snapshot.get("session_id") != owner["session_id"] or not isinstance(fingerprint, str):
        return None
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)):
        return None
    if any(not isinstance(action, Mapping) or action.get("action_type") not in {"attack", "manual_switch"} or not isinstance(action.get("action_id"), str) or not isinstance(action.get("identity"), str) for action in actions):
        return None
    return deepcopy(dict(owner)), fingerprint, actions


def _matching_incoming_action_id(
    *, incoming: Any, owner: Mapping[str, Any], fingerprint: str, actions: Sequence[Mapping[str, Any]],
) -> str | None:
    if not isinstance(incoming, Mapping) or incoming.get("source_branch_fingerprint") != fingerprint:
        return None
    incoming_owner = incoming.get("owner")
    hp = incoming.get("hp_authority")
    fainted = incoming.get("fainted_authority")
    current = incoming.get("current_state")
    if incoming.get("provenance") != "identity_bound_incoming_current_state_v1" or not _owner(incoming_owner):
        return None
    if incoming_owner["session_id"] != owner["session_id"] or incoming_owner["side"] != owner["side"] or incoming_owner == owner:
        return None
    if not _known_hp(hp) or not isinstance(fainted, Mapping) or fainted.get("status") != "known" or fainted.get("value") is not (hp["current_hp"] == 0):
        return None
    if not isinstance(current, Mapping) or current.get("current_state_session_id") != owner["session_id"]:
        return None
    action_id = f"manual_switch:{incoming_owner['pokemon_id']}"
    return action_id if any(action.get("action_id") == action_id for action in actions) else None


def _matching_execution_bundle(selection: Mapping[str, Any], bundle: Any) -> bool:
    return isinstance(bundle, Mapping) and bundle.get("status") == "resolved" and bundle.get("schema_version") == _EXECUTION_SCHEMA and all(
        bundle.get(key) == selection.get(key)
        for key in ("session_id", "decision_branch_fingerprint", "decision_owner")
    )


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _known_hp(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool) and isinstance(value.get("maximum_hp"), int) and not isinstance(value.get("maximum_hp"), bool) and value["maximum_hp"] > 0 and 0 <= value["current_hp"] <= value["maximum_hp"]


def _record(action_id: str, authority_class: str, reason: str, authority: Any = None) -> dict[str, Any]:
    return {"action_id": action_id, "authority_class": authority_class, "reason": reason, "authority": authority}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
