"""Atomic self-side execution of one already-allowed forced replacement."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_executable_switch_transition import execute_materialized_switch_entry
from llm.advisor_forced_switch_request import materialize_forced_switch_request
from llm.advisor_forced_switch_replacement import AUTHORITY_PROVENANCE, AUTHORITY_SCHEMA
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_persistent_effect_authority import materialize_persistent_effect_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state


_FAMILIES = ("aqua_ring", "ingrain", "leech_seed")
_CONTEXTS = {
    "aqua_ring": ("aqua_ring_persistent_effect_context", "detached-aqua-ring-persistent-effect-v1", "trusted_aqua_ring_persistent_effect_state"),
    "ingrain": ("ingrain_persistent_effect_context", "detached-ingrain-persistent-effect-v1", "trusted_ingrain_persistent_effect_state"),
    "leech_seed": ("leech_seed_persistent_effect_context", "detached-leech-seed-persistent-effect-v1", "trusted_leech_seed_persistent_effect_state"),
}


def execute_allowed_self_forced_switch(
    *, source_branch: Mapping[str, Any], source_branch_fingerprint: str,
    forced_switch_request: Mapping[str, Any], cancellation_decision: Mapping[str, Any],
    replacement_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute one allowed F0 self replacement; never chooses a replacement."""
    prepared = materialize_allowed_forced_replacement(
        source_branch=source_branch, source_branch_fingerprint=source_branch_fingerprint,
        forced_switch_request=forced_switch_request, cancellation_decision=cancellation_decision,
        replacement_authority=replacement_authority,
    )
    if prepared.get("status") != "resolved": return prepared
    outgoing = forced_switch_request["target_owner"]
    if outgoing.get("side") != "self":
        return _result("unsupported", "opponent_forced_switch_execution_out_of_scope")
    entry = execute_materialized_switch_entry(
        materialized_switch=prepared, entry_authority=replacement_authority["entry_authority"],
    )
    if entry.get("status") == "unsupported" and entry.get("reason") == "replacement_required_after_entry_hazard_ko":
        return {**entry, "source_branch_fingerprint": source_branch_fingerprint, "forced_switch_request": deepcopy(dict(forced_switch_request)), "replacement_authority": deepcopy(dict(replacement_authority)), "atomic_execution": True, "boundary": {"phase": "forced_switch_terminal_entry"}}
    if entry.get("status") != "resolved": return entry
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": entry["resulting_branch_fingerprint"],
        "post_switch_branch_fingerprint": prepared["resulting_branch_fingerprint"],
        "post_entry_branch_fingerprint": entry["post_entry_branch_fingerprint"],
        "next_state": entry["next_state"], "entry_effect_result": entry["entry_effect_result"],
        "consequence_trace": entry["consequence_trace"], "atomic_execution": True,
        "boundary": {"phase": "post_forced_switch_entry"},
        "limitations": ["self_side_only", "replacement_already_resolved", "no_replacement_loop", "no_reducer_or_runtime_writeback"],
    }


def materialize_allowed_forced_replacement(
    *, source_branch: Mapping[str, Any], source_branch_fingerprint: str,
    forced_switch_request: Mapping[str, Any], cancellation_decision: Mapping[str, Any],
    replacement_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Create one side-neutral post-replacement/pre-entry branch from F0 authority."""
    if fingerprint_transition_preview_state(source_branch) != source_branch_fingerprint:
        return _result("rejected", "stale_or_invalid_forced_switch_execution_branch")
    request = materialize_forced_switch_request(branch_state=source_branch, source_branch_fingerprint=source_branch_fingerprint, observed_request=forced_switch_request)
    if request.get("status") != "resolved": return request
    outgoing = forced_switch_request.get("target_owner")
    if not _valid_allowed_decision(cancellation_decision, source_branch_fingerprint, forced_switch_request, outgoing):
        return _result("rejected", "forced_switch_execution_not_allowed")
    if not _valid_authority(replacement_authority, source_branch_fingerprint, outgoing):
        return _result("rejected", "stale_or_invalid_forced_switch_replacement_authority")
    materialized = materialize_incoming_active_branch(
        source_branch=source_branch, source_branch_fingerprint=source_branch_fingerprint,
        incoming_authority=replacement_authority["incoming_authority"],
    )
    if materialized.get("status") != "resolved": return materialized
    prepared = _attach_forced_replacement_state(
        materialized=materialized, source_branch_fingerprint=source_branch_fingerprint,
        source_branch=source_branch, replacement_authority=replacement_authority,
    )
    if prepared.get("status") != "resolved": return prepared
    return {
        "status": "resolved", "source_branch_fingerprint": source_branch_fingerprint,
        "resulting_branch_fingerprint": prepared["resulting_branch_fingerprint"],
        "next_state": prepared["next_state"], "materialization_trace": prepared["materialization_trace"],
        "boundary": {"phase": "post_forced_switch_pre_entry"},
        "limitations": ["replacement_already_resolved", "entry_execution_separate", "no_reducer_or_runtime_writeback"],
    }


def _attach_forced_replacement_state(*, materialized: Mapping[str, Any], source_branch_fingerprint: str, source_branch: Mapping[str, Any], replacement_authority: Mapping[str, Any]) -> dict[str, Any]:
    state = deepcopy(materialized["next_state"])
    incoming = replacement_authority["incoming_authority"]["owner"]
    incoming_side = incoming["side"]
    retained_side = "opponent" if incoming_side == "self" else "self"
    retained = state["active"][retained_side]
    source_bundle = source_branch.get("branch_persistent_effect_authority")
    rows = source_bundle.get("states") if isinstance(source_bundle, Mapping) else None
    if not isinstance(rows, list): return _result("incomplete", "persistent_effect_authority_unknown")
    states = {incoming_side: replacement_authority["incoming_authority"]["persistent_effect_states"], retained_side: {}}
    for family in _FAMILIES:
        match = [row for row in rows if isinstance(row, Mapping) and row.get("family") == family and row.get("owner") == _owner(retained)]
        if len(match) != 1 or match[0].get("state") not in {"known_active", "known_inactive", "unknown"}: return _result("rejected", "stale_or_invalid_opponent_persistent_effect_authority")
        states[retained_side][family] = {key: deepcopy(match[0][key]) for key in ("state", "provenance", "source_slot") if key in match[0]}
    owners = {incoming_side: _owner(incoming), retained_side: _owner(retained)}
    state["branch_persistent_effect_authority"] = materialize_persistent_effect_authority(owners=owners, source_branch_fingerprint=source_branch_fingerprint, states=states)
    for family, (key, schema, provenance) in _CONTEXTS.items():
        context_rows = []
        for side, owner in owners.items():
            row = states[side][family]
            item = {"owner": deepcopy(owner), "state": row["state"]}
            if family == "leech_seed" and row["state"] == "known_active": item["source_slot"] = deepcopy(row["source_slot"])
            context_rows.append(item)
        state[key] = {"schema_version": schema, "session_id": incoming["session_id"], "source_branch_fingerprint": source_branch_fingerprint, "provenance": provenance, "states": context_rows}
    state["forced_switch_bench_record"] = {
        "schema_version": "detached-forced-switch-bench-record-v1", "source_branch_fingerprint": source_branch_fingerprint,
        "owner": deepcopy(replacement_authority["outgoing_bench_authority"]["owner"]),
        "hp_authority": deepcopy(replacement_authority["outgoing_bench_authority"]["hp_authority"]),
        "fainted_authority": deepcopy(replacement_authority["outgoing_bench_authority"]["fainted_authority"]),
        "retained_current_state": deepcopy(replacement_authority["outgoing_bench_authority"]["retained_current_state"]),
        "persistent_effects": {family: "cleared_on_forced_switch" for family in _FAMILIES},
        "provenance": "trusted_forced_switch_outgoing_bench_v1",
    }
    fp = fingerprint_transition_preview_state(state)
    if fp is None: return _result("rejected", "unserializable_forced_switch_materialization")
    trace = [*deepcopy(materialized.get("materialization_trace", [])), {"sequence": 2, "event": "forced_switch_outgoing_retained", "execution_status": "executed", "outgoing_owner": deepcopy(replacement_authority["outgoing_bench_authority"]["owner"]), "persistent_effects": "cleared_non_transfer", "provenance": "trusted_forced_switch_outgoing_bench_v1"}]
    return {"status": "resolved", "source_branch_fingerprint": source_branch_fingerprint, "resulting_branch_fingerprint": fp, "next_state": state, "materialization_trace": trace}


def _valid_authority(value: Any, fingerprint: str, outgoing: Any) -> bool:
    return isinstance(value, Mapping) and value.get("schema_version") == AUTHORITY_SCHEMA and value.get("source_branch_fingerprint") == fingerprint and value.get("outgoing_owner") == outgoing and value.get("session_id") == outgoing.get("session_id") and value.get("provenance") == AUTHORITY_PROVENANCE and isinstance(value.get("incoming_authority"), Mapping) and isinstance(value.get("outgoing_bench_authority"), Mapping) and isinstance(value.get("entry_authority"), Mapping)


def _valid_allowed_decision(value: Any, fingerprint: str, request: Mapping[str, Any], outgoing: Any) -> bool:
    return isinstance(value, Mapping) and value.get("schema_version") == "forced-switch-cancellation-decision-v1" and value.get("source_branch_fingerprint") == fingerprint and value.get("forced_switch_request") == dict(request) and value.get("target_owner") == outgoing and value.get("decision") == "allowed_to_proceed" and value.get("provenance") == "trusted_canonical_showdown_ingrain_drag_out"


def _owner(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "reason": reason}
