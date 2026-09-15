"""Atomic production admission for explicitly confirmed phazing events."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_forced_switch_execution import execute_allowed_forced_switch
from llm.advisor_forced_switch_replacement import materialize_forced_switch_replacement_authority
from llm.advisor_forced_switch_request import decide_forced_switch_cancellation
from llm.advisor_lifecycle_confirmation import HP_TRANSITION_SOURCE, SWITCH_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observed_damage_plus_phazing import materialize_observed_damage_plus_phazing_result
from llm.advisor_observed_forced_switch_source_application import materialize_observed_forced_switch_source_application
from llm.advisor_roster_mechanics import _base_record
from llm.advisor_runtime_d0_forced_switch_source_authority import freeze_runtime_d0_forced_switch_source_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_incoming_current_state_authority, resolve_runtime_incoming_owner
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "forced-switch-entry-consequence-audit-v1"
_SOURCE_MOVES = {"roar", "whirlwind"}
_DAMAGE_MOVES = {"dragon-tail", "circle-throw"}


def admit_forced_switch_phazing(*, runtime_session_manager, captured_session_id, target_side, move_id, incoming_pokemon_id, turn_number, hp_after=None):
    """Validate detached phazing, then commit one all-or-nothing observation batch."""
    if target_side not in {"self", "opponent"} or move_id not in _SOURCE_MOVES | _DAMAGE_MOVES or not isinstance(incoming_pokemon_id, str) or not incoming_pokemon_id:
        return _result("rejected", "invalid_forced_switch_confirmation")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready": return _result("rejected", "runtime_snapshot_unavailable")
    source = freeze_runtime_d0_forced_switch_source_authority(runtime_snapshot=snapshot, target_side=target_side)
    if source.get("status") != "resolved": return _result("rejected", source.get("reason", "forced_switch_source_unavailable"))
    prepared = _prepare_runtime_replacement_branch(source, snapshot, incoming_pokemon_id)
    if prepared.get("status") != "resolved": return _result(prepared.get("status", "rejected"), prepared.get("reason", "replacement_unavailable"))
    branch, fp, request, hp_transition = prepared["branch_state"], prepared["source_branch_fingerprint"], None, None
    if move_id in _SOURCE_MOVES:
        observed = {"schema_version": "observed-forced-switch-source-application-v1", "session_id": source["session_id"], "source_branch_fingerprint": fp, "user": source["active_owners"]["opponent" if target_side == "self" else "self"], "target_owner": source["target_owner"], "move_id": move_id, "applied_effect": "drag_out", "result": "applied", "provenance": "trusted_observed_forced_switch_source_application_v1"}
        materialized = materialize_observed_forced_switch_source_application(branch_state=branch, source_branch_fingerprint=fp, observed_source_result=observed)
        if materialized.get("status") != "resolved": return _result("rejected", materialized.get("reason", "observed_source_rejected"))
        request = materialized["forced_switch_request"]
    else:
        before = _active_hp(snapshot["state"], target_side)
        if not isinstance(hp_after, int) or isinstance(hp_after, bool) or not isinstance(before, int) or hp_after < 0 or hp_after >= before:
            return _result("rejected", "exact_phazing_hp_transition_required")
        observed = {"schema_version": "observed-damage-plus-phazing-result-v1", "session_id": source["session_id"], "source_branch_fingerprint": fp, "user": source["active_owners"]["opponent" if target_side == "self" else "self"], "target_owner": source["target_owner"], "move_id": move_id, "damage_amount": before - hp_after, "damaging_hit_result": "applied", "drag_out_result": "drag_out_requested" if hp_after else "not_applied", "provenance": "trusted_observed_damage_plus_phazing_result_v1"}
        materialized = materialize_observed_damage_plus_phazing_result(branch_state=branch, source_branch_fingerprint=fp, observed_result=observed)
        if materialized.get("status") != "resolved": return _result("rejected", materialized.get("reason", "observed_damage_phazing_rejected"))
        hp_transition = (before, hp_after)
        if materialized.get("drag_out") == "not_applied": return _commit(runtime_session_manager, captured_session_id, snapshot, source, hp_transition, None, turn_number)
        branch, fp, request = materialized["next_state"], materialized["resulting_branch_fingerprint"], materialized["forced_switch_request"]
        # The observed replacement is bound at the post-damage F0 boundary: its
        # outgoing bench authority must therefore carry the exact observed HP.
        prepared["observed_replacement"] = _rebind_observed_replacement(
            prepared["observed_replacement"], branch, fp, source["target_owner"],
        )
    decision = decide_forced_switch_cancellation(branch_state=branch, source_branch_fingerprint=fp, forced_switch_request=request)
    if decision.get("status") == "incomplete": return _result("incomplete", decision.get("reason", "ingrain_unknown"))
    if decision.get("decision") == "cancelled": return _commit(runtime_session_manager, captured_session_id, snapshot, source, hp_transition, None, turn_number, cancellation="cancelled")
    authority = materialize_forced_switch_replacement_authority(branch_state=branch, source_branch_fingerprint=fp, forced_switch_request=request, cancellation_decision=decision, observed_replacement=prepared["observed_replacement"])
    if authority.get("status") != "resolved": return _result("rejected", authority.get("reason", "replacement_authority_rejected"))
    executed = execute_allowed_forced_switch(
        source_branch=branch, source_branch_fingerprint=fp,
        forced_switch_request=request, cancellation_decision=decision,
        replacement_authority=authority, defer_abilities=True,
    )
    audit = audit_forced_switch_entry_consequences(executed=executed, source_runtime_fingerprint=source["source_runtime_fingerprint"], source_branch_fingerprint=fp, outgoing_owner=source["target_owner"], incoming_owner=prepared["incoming_owner"])
    if audit.get("status") != "resolved": return _result(audit.get("status", "unsupported"), audit.get("reason", "entry_consequence_unrepresentable"))
    return _commit(runtime_session_manager, captured_session_id, snapshot, source, hp_transition, prepared["incoming_owner"], turn_number, audit=audit)


def audit_forced_switch_entry_consequences(*, executed, source_runtime_fingerprint, source_branch_fingerprint, outgoing_owner, incoming_owner):
    """Accept only a neutral entry whose runtime writeback is exactly canonical."""
    base = {"schema_version": SCHEMA_VERSION, "session_id": outgoing_owner.get("session_id") if isinstance(outgoing_owner, Mapping) else None, "source_runtime_fingerprint": source_runtime_fingerprint, "source_branch_fingerprint": source_branch_fingerprint, "outgoing_owner": deepcopy(outgoing_owner), "incoming_owner": deepcopy(incoming_owner), "provenance": "forced_switch_entry_consequence_audit_v1"}
    if not isinstance(executed, Mapping): return {"status": "rejected", "reason": "invalid_detached_execution", **base}
    if executed.get("status") == "unsupported" and executed.get("reason") == "replacement_required_after_entry_hazard_ko": return {"status": "unsupported", "reason": "replacement_required_after_entry_hazard_ko", "terminal_boundary": "replacement_required_after_entry_hazard_ko", "unsupported_consequences": ["entry_hazard_ko"], **base}
    if executed.get("status") != "resolved": return {"status": "incomplete", "reason": executed.get("reason", "detached_entry_incomplete"), "unsupported_consequences": ["entry_effects"], **base}
    entry = executed.get("entry_effect_result", {})
    if not isinstance(entry, Mapping) or entry.get("damage") != 0 or any(entry.get(name, {}).get("outcome") not in {"absent", "not_applicable", None} for name in ("toxic_spikes_result", "sticky_web_result", "intimidate_result", "download_result", "trace_result", "sturdy_result", "weather_result")):
        return {"status": "unsupported", "reason": "non_neutral_entry_consequence", "unsupported_consequences": ["entry_effects"], **base}
    return {"status": "resolved", "consequences": {"switch": True, "hp_transitions": [], "condition_changes": [], "stage_changes": [], "field_changes": []}, "unsupported_consequences": [], "terminal_boundary": None, **base}


def _prepare_runtime_replacement_branch(source, snapshot, incoming_pokemon_id):
    state, target = snapshot["state"], source["target_owner"]
    # Re-freeze D0 for the same target; this keeps incoming resolution side-neutral.
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=target)
    incoming = resolve_runtime_incoming_owner(strategy_d0=d0, runtime_snapshot=snapshot, pokemon_id=incoming_pokemon_id)
    if incoming.get("status") != "resolved": return incoming
    incoming_owner = incoming["incoming_owner"]
    incoming_authority = freeze_runtime_incoming_current_state_authority(strategy_d0=d0, runtime_snapshot=snapshot, incoming_owner=incoming_owner)
    if incoming_authority.get("status") != "resolved": return incoming_authority
    branch = deepcopy(source["branch_state"]); raw_incoming = state[f"{incoming_owner['side']}_side"]["pokemon"][incoming_owner["slot_index"]]
    target_record = _base_record(source["session_id"], incoming_owner["slot_index"], incoming_owner["pokemon_id"], raw_incoming); target_record["side"] = incoming_owner["side"]
    branch.setdefault("current_state", {})[f"{incoming_owner['side']}_roster_mechanics_context"] = {"session_id": source["session_id"], "side": incoming_owner["side"], "entries": [deepcopy(target_record)]}
    fp = fingerprint_transition_preview_state(branch)
    persistent = {family: {"state": "unknown"} for family in ("aqua_ring", "ingrain", "leech_seed")}
    incoming_authority = deepcopy(incoming_authority); incoming_authority["persistent_effect_states"] = persistent
    outgoing_raw = state[f"{target['side']}_side"]["pokemon"][target["slot_index"]]
    observed = {"schema_version": "observed-forced-replacement-result-v1", "session_id": source["session_id"], "source_branch_fingerprint": fp, "outgoing_owner": deepcopy(target), "incoming_authority": incoming_authority, "outgoing_bench_authority": {"owner": deepcopy(target), "hp_authority": {"status": "known", "current_hp": outgoing_raw.get("current_hp"), "maximum_hp": outgoing_raw.get("max_hp")}, "fainted_authority": {"status": "known", "value": outgoing_raw.get("fainted")}, "retained_current_state": {"condition": deepcopy(outgoing_raw.get("condition")), "item": deepcopy(outgoing_raw.get("known_item")), "types": deepcopy(outgoing_raw.get("current_type")), "ability": deepcopy(outgoing_raw.get("current_ability"))}, "provenance": "trusted_forced_switch_outgoing_bench_v1"}, "entry_authority": {"hazards": deepcopy(source["switch_hazard_authority"]), "target_roster_mechanics": deepcopy(target_record), "intimidate_authority": None, "download_authority": None, "field_state_context": None, "provenance": "trusted_forced_switch_entry_authority_v1"}, "replacement_status": "replacement_resolved", "provenance": "trusted_observed_forced_replacement_result_v1"}
    return {"status": "resolved", "branch_state": branch, "source_branch_fingerprint": fp, "incoming_owner": incoming_owner, "observed_replacement": observed}


def _rebind_observed_replacement(observed, branch, fingerprint, outgoing_owner):
    """Bind trusted replacement evidence to the exact detached F0 boundary."""
    rebound = deepcopy(observed)
    active = branch["active"][outgoing_owner["side"]]
    rebound["source_branch_fingerprint"] = fingerprint
    rebound["outgoing_bench_authority"]["hp_authority"] = {
        "status": "known",
        "current_hp": active["current_hp"],
        "maximum_hp": active["max_hp"],
    }
    rebound["outgoing_bench_authority"]["fainted_authority"] = {
        "status": "known", "value": active["fainted"],
    }
    return rebound


def _commit(manager, session, snapshot, source, hp_transition, incoming_owner, turn, cancellation=None, audit=None):
    confirmations = []; boundary = LifecycleConfirmationBoundary(session, source["active_owners"])
    if hp_transition is not None:
        sequence = manager.allocate_observation_sequence()["observation_sequence"]
        result = boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before": hp_transition[0], "hp_after": hp_transition[1]}, session_id=session, source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side=source["target_side"], slot_index=source["target_owner"]["slot_index"], pokemon_id=source["target_owner"]["pokemon_id"], observation_id=f"{session}:phazing-hp-{sequence}", turn_number=turn)
        if result.get("status") != "confirmed": return _result("rejected", "hp_confirmation_rejected")
        result["observation"]["observation_sequence"] = sequence; confirmations.append(result)
    if incoming_owner is not None:
        sequence = manager.allocate_observation_sequence()["observation_sequence"]
        target = source["target_owner"]
        result = boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": target["slot_index"], "switch_out_pokemon_id": target["pokemon_id"], "switch_in_slot_index": incoming_owner["slot_index"], "switch_in_pokemon_id": incoming_owner["pokemon_id"]}, session_id=session, source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side=source["target_side"], slot_index=target["slot_index"], pokemon_id=target["pokemon_id"], observation_id=f"{session}:phazing-switch-{sequence}", turn_number=turn)
        if result.get("status") != "confirmed": return _result("rejected", "switch_confirmation_rejected")
        result["observation"]["observation_sequence"] = sequence; confirmations.append(result)
    if not confirmations: return {"status": "resolved", "reason": cancellation, "observation_transaction": []}
    collection = manager.read_collection_snapshot(); rows = [*collection.get("ordered_observations", []), *(row["observation"] for row in confirmations)]; rows.sort(key=lambda row: (row["observation_sequence"], row["observation_id"]))
    preview = manager.preview(session, {**collection, "ordered_observations": rows})
    if preview.get("status") != "preview_ready": return _result("rejected", "atomic_preview_rejected")
    admitted = manager.admit_confirmations_atomically(session, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}: return _result("rejected", "atomic_admission_rejected")
    applied = manager.apply(session, manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}: return _result("rejected", "atomic_application_rejected")
    committed_owner = None
    if incoming_owner is not None:
        committed = manager.read_state().get("state", {})
        active_slot = committed.get(f"{incoming_owner['side']}_side", {}).get("active_slot_index")
        active = committed.get(f"{incoming_owner['side']}_side", {}).get("pokemon", {}).get(active_slot)
        if not isinstance(active, Mapping) or active_slot != incoming_owner["slot_index"] or active.get("pokemon_id") != incoming_owner["pokemon_id"]:
            return _result("rejected", "committed_target_owner_mismatch")
        committed_owner = deepcopy(incoming_owner)
    return {"status": "resolved", "reason": cancellation, "committed_owner": committed_owner, "observation_transaction": [deepcopy(row["observation"]) for row in confirmations], "audit": deepcopy(audit)}


def _active_hp(state, side):
    slot = state.get(f"{side}_side", {}).get("active_slot_index") if isinstance(state, Mapping) else None
    pokemon = state.get(f"{side}_side", {}).get("pokemon", {}).get(slot) if isinstance(state, Mapping) else None
    return pokemon.get("current_hp") if isinstance(pokemon, Mapping) else None
def _result(status, reason): return {"status": status, "reason": reason, "observation_transaction": []}
