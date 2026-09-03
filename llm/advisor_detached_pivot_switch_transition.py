"""Materialize a validated pivot continuation from one detached attack terminal."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch
from llm.advisor_executable_switch_transition import execute_materialized_switch_entry
from llm.advisor_runtime_strategy_d0 import freeze_runtime_incoming_current_state_authority
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "detached-damage-pivot-switch-transition-v1"


def materialize_detached_damage_pivot_switch(*, intermediate_authority: Mapping[str, Any], pivot_authority: Mapping[str, Any], entry_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Apply one already-authorized voluntary pivot to an exact post-hit branch.

    The incoming authority is frozen from the post-hit hypothetical runtime
    snapshot; no attack result is recomputed or replayed here.
    """
    if not isinstance(intermediate_authority, Mapping) or intermediate_authority.get("status") != "resolved":
        return _result("rejected", "pivot_intermediate_authority_invalid")
    if not isinstance(pivot_authority, Mapping) or pivot_authority.get("status") != "applies":
        return _result("rejected", "pivot_continuation_not_applicable")
    d0 = intermediate_authority.get("predictive_strategy_d0")
    snapshot = intermediate_authority.get("predictive_runtime_snapshot")
    incoming_owner = pivot_authority.get("selected_replacement_owner")
    source = d0.get("strategy_state") if isinstance(d0, Mapping) else None
    fingerprint = d0.get("strategy_preview_fingerprint") if isinstance(d0, Mapping) else None
    expected = {"session_id": intermediate_authority.get("session_id"), "source_runtime_fingerprint": intermediate_authority.get("source_runtime_fingerprint"), "source_branch_fingerprint": intermediate_authority.get("source_branch_fingerprint"), "decision_owner": intermediate_authority.get("decision_owner")}
    if any(pivot_authority.get(key) != value for key, value in expected.items()) or not isinstance(d0, Mapping) or not isinstance(snapshot, Mapping) or not isinstance(source, Mapping) or not isinstance(fingerprint, str) or not isinstance(incoming_owner, Mapping):
        return _result("rejected", "pivot_continuation_binding_mismatch")
    if fingerprint_transition_preview_state(source) != fingerprint:
        return _result("rejected", "pivot_post_attack_branch_stale")
    incoming = freeze_runtime_incoming_current_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, incoming_owner=incoming_owner)
    if incoming.get("status") != "resolved":
        return _result(incoming.get("status", "incomplete"), incoming.get("reason", "pivot_incoming_authority_unavailable"))
    materialized = materialize_incoming_active_branch(source_branch=source, source_branch_fingerprint=fingerprint, incoming_authority=incoming)
    if materialized.get("status") != "resolved":
        return _result(materialized.get("status", "rejected"), materialized.get("reason", "pivot_switch_materialization_unavailable"))
    if entry_authority is not None:
        entered = execute_materialized_switch_entry(materialized_switch=materialized, entry_authority=entry_authority)
        if entered.get("status") != "resolved":
            return _result(entered.get("status", "incomplete"), entered.get("reason", "pivot_switch_entry_unavailable"))
        materialized = {**materialized, "next_state": entered["next_state"], "resulting_branch_fingerprint": entered["resulting_branch_fingerprint"], "materialization_trace": entered.get("consequence_trace", materialized.get("materialization_trace", []))}
    state = materialized["next_state"]
    runtime_state = deepcopy(dict(snapshot["state"]))
    runtime_state["self_side"]["active_slot_index"] = incoming_owner["slot_index"]
    # A manual-switch permission is identity-bound to the outgoing active.
    # Keeping it after the forced post-damage replacement would both leak a
    # stale authority and make the runtime-shaped handoff invalid.
    runtime_state["self_side"].pop("switch_permission_context", None)
    raw_incoming = runtime_state["self_side"]["pokemon"][incoming_owner["slot_index"]]
    raw_incoming["current_hp"] = state["active"]["self"]["current_hp"]
    raw_incoming["max_hp"] = state["active"]["self"]["max_hp"]
    raw_incoming["fainted"] = state["active"]["self"]["fainted"]
    runtime_snapshot = {"status": "runtime_snapshot_ready", "session_id": d0["session_id"], "state": runtime_state, "state_fingerprint": state_fingerprint(runtime_state)}
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "source_first_action_leaf_id": intermediate_authority.get("source_first_action_leaf_id"), "pivot_authority": deepcopy(dict(pivot_authority)), "incoming_authority": deepcopy(dict(incoming)), "resulting_active_owner": deepcopy(dict(state["active"]["self"])), "next_state": deepcopy(state), "runtime_snapshot": runtime_snapshot, "resulting_branch_fingerprint": materialized["resulting_branch_fingerprint"], "materialization_trace": deepcopy(materialized["materialization_trace"]), "provenance": "exact_post_attack_intermediate_to_pivot_incoming_active_v1"}


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
