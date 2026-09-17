"""Atomic admission of explicitly observed contact-reactive status results."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_lifecycle_confirmation import (CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE,
    CONTACT_REACTIVE_STATUS_RESULT_SOURCE, EXECUTED_MOVE_SOURCE, HP_TRANSITION_SOURCE,
    USER_TRUST, LifecycleConfirmationBoundary)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata
from llm.advisor_runtime_d0_contact_reactive_status_authority import freeze_runtime_d0_contact_reactive_status_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0

_ABILITIES = {"static": "paralysis", "flame-body": "burn", "poison-point": "poison"}

def admit_observed_contact_reactive_status_result(*, runtime_session_manager, captured_session_id, attacker_side, move_id, source_action_id, target_hp_after, outcome, turn_number):
    """Commit one observed damaging contact result, or reuse its exact receipt."""
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager) or attacker_side not in {"self", "opponent"} or outcome not in {"activation", "no_activation"} or not _token(move_id) or not _token(source_action_id) or not _positive(turn_number) or not _nonnegative(target_hp_after):
        return _result("rejected", "invalid_observed_contact_request")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready": return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    state = snapshot.get("state"); attacker, defender = _active_owner(state, attacker_side), _active_owner(state, _other(attacker_side))
    if attacker is None or defender is None: return _result("rejected", "observed_contact_owner_unavailable")
    collection = runtime_session_manager.read_collection_snapshot()
    receipt = _receipt(collection, captured_session_id, source_action_id)
    if receipt is not None: return _reuse_receipt(receipt, attacker, defender, move_id, source_action_id, target_hp_after, outcome, turn_number, runtime_session_manager)
    execution = _execution(collection, captured_session_id, source_action_id)
    if execution is not None and not _execution_matches(execution, attacker, move_id, turn_number): return _result("rejected", "conflicting_observed_contact_source_action")
    target = _pokemon(state, defender); before = target.get("current_hp") if isinstance(target, Mapping) else None
    if not _nonnegative(before) or target_hp_after >= before: return _result("rejected", "observed_contact_hp_transition_invalid")
    if target_hp_after == 0: return _result("rejected", "observed_contact_ko_requires_faint_lifecycle")
    metadata = canonical_move_contact_metadata(move_id)
    if not isinstance(metadata, Mapping) or metadata.get("status") != "resolved": return _result(metadata.get("status", "rejected") if isinstance(metadata, Mapping) else "rejected", metadata.get("reason", "contact_metadata_unavailable") if isinstance(metadata, Mapping) else "contact_metadata_unavailable")
    if metadata.get("contact_state") != "contact": return _result("rejected", "observed_contact_non_contact_move")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=attacker)
    if d0.get("status") != "resolved": return _result("incomplete", "fresh_runtime_d0_unavailable")
    action = {"action_id": source_action_id, "action_type": "attack", "identity": move_id}
    contact = {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "action_id": source_action_id, "attacker": attacker, "target": defender, "move_id": move_id, "contact_state": "contact", "canonical_contact_metadata": deepcopy(dict(metadata)), "provenance": "observed_runtime_canonical_contact_evidence_v1"}
    authority = freeze_runtime_d0_contact_reactive_status_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=attacker, defender=defender, source_action=action, contact_authority=contact, source_hit={"source_action_id": source_action_id, "source_move_id": move_id, "hit_index": 1, "actual_damage": before-target_hp_after, "target_routing": "target"})
    if authority.get("status") != "resolved" or authority.get("outcome") != "applies" or authority.get("transition_applies") is not True: return _result(authority.get("status", "rejected"), authority.get("blocked_reason", authority.get("reason", "observed_contact_status_ineligible")))
    ability = authority.get("reactive_ability")
    if ability not in _ABILITIES: return _result("rejected", "unsupported_observed_contact_reactive_ability")
    payload = _payload(attacker, defender, source_action_id, move_id, ability, outcome, before, target_hp_after)
    confirmations = _confirmations(captured_session_id, attacker, defender, payload, turn_number, execution is None)
    if confirmations is None: return _result("rejected", "observed_contact_confirmation_rejected")
    for row in confirmations:
        allocated = runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id: return _result("rejected", "observation_sequence_unavailable")
        row["observation"]["observation_sequence"] = allocated["observation_sequence"]
    preview = _preview(collection, confirmations)
    if preview is None or runtime_session_manager.preview(captured_session_id, preview).get("status") != "preview_ready": return _result("rejected", "observed_contact_preview_rejected")
    if runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations).get("status") not in {"added", "duplicate"}: return _result("rejected", "observed_contact_admission_rejected")
    if runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot()).get("status") not in {"applied", "already_applied"}: return _result("rejected", "observed_contact_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    before_actor = _pokemon(state, attacker)
    if not _committed_ok(committed, attacker, defender, target_hp_after, ability, outcome, before_actor): return _result("rejected", "observed_contact_committed_runtime_verification_failed")
    fresh = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=attacker)
    if target_hp_after > 0 and (fresh.get("status") != "resolved" or fresh.get("source_runtime_fingerprint") == d0.get("source_runtime_fingerprint")): return _result("rejected", "observed_contact_fresh_d0_verification_failed")
    return {"status": "resolved", "reason": None, "owner": deepcopy(defender), "observations": [deepcopy(x["observation"]) for x in confirmations], "runtime_snapshot": committed, "strategy_d0": fresh, "idempotent": False}

def _confirmations(session, attacker, defender, payload, turn, create_execution):
    boundary = LifecycleConfirmationBoundary(session, {attacker["side"]: attacker, defender["side"]: defender}); rows = []
    if create_execution: rows.append(boundary.confirm(event_kind="executed_move_observed", payload={"move_id":payload["move_id"],"source_action_id":payload["source_action_id"]}, session_id=session, source=EXECUTED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side=attacker["side"], slot_index=attacker["slot_index"], pokemon_id=attacker["pokemon_id"], observation_id=f"{session}:contact-reactive:{payload['source_action_id']}:execution", turn_number=turn))
    rows.append(boundary.confirm(event_kind="contact_reactive_status_result_observed", payload=payload, session_id=session, source=CONTACT_REACTIVE_STATUS_RESULT_SOURCE, trust=USER_TRUST, confirmed=True, side=defender["side"], slot_index=defender["slot_index"], pokemon_id=defender["pokemon_id"], observation_id=f"{session}:contact-reactive:{payload['source_action_id']}:result", turn_number=turn))
    rows.append(boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before":payload["hp_before"],"hp_after":payload["hp_after"]}, session_id=session, source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side=defender["side"], slot_index=defender["slot_index"], pokemon_id=defender["pokemon_id"], observation_id=f"{session}:contact-reactive:{payload['source_action_id']}:hp", turn_number=turn))
    if payload["outcome"] == "activation": rows.append(boundary.confirm(event_kind="current_condition_observed", payload={"condition":_ABILITIES[payload["reactive_ability"]]}, session_id=session, source=CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side=attacker["side"], slot_index=attacker["slot_index"], pokemon_id=attacker["pokemon_id"], observation_id=f"{session}:contact-reactive:{payload['source_action_id']}:condition", turn_number=turn))
    return rows if all(row.get("status") == "confirmed" for row in rows) else None

def _reuse_receipt(receipt, attacker, defender, move, action, after, outcome, turn, manager):
    payload = receipt.get("payload") if isinstance(receipt, Mapping) else None; before = payload.get("hp_before") if isinstance(payload, Mapping) else None
    if receipt.get("turn_number") != turn or payload != _payload(attacker, defender, action, move, payload.get("reactive_ability") if isinstance(payload, Mapping) else None, outcome, before, after): return _result("rejected", "conflicting_observed_contact_source_action")
    collection = manager.read_collection_snapshot()
    ability = payload.get("reactive_ability") if isinstance(payload, Mapping) else None
    execution = _execution(collection, receipt.get("session_id"), action)
    hp = next((x for x in collection.get("ordered_observations", []) if isinstance(x, Mapping) and x.get("observation_id") == f"{receipt.get('session_id')}:contact-reactive:{action}:hp"), None)
    condition = next((x for x in collection.get("ordered_observations", []) if isinstance(x, Mapping) and x.get("observation_id") == f"{receipt.get('session_id')}:contact-reactive:{action}:condition"), None)
    hp_ok = isinstance(hp, Mapping) and hp.get("event_kind") == "exact_hp_transition_observed" and hp.get("source") == HP_TRANSITION_SOURCE and hp.get("session_id") == receipt.get("session_id") and hp.get("turn_number") == receipt.get("turn_number") and (hp.get("side"), hp.get("slot_index"), hp.get("pokemon_id"), hp.get("payload", {}).get("hp_before"), hp.get("payload", {}).get("hp_after")) == (defender["side"], defender["slot_index"], defender["pokemon_id"], before, after)
    condition_ok = isinstance(condition, Mapping) and condition.get("event_kind") == "current_condition_observed" and condition.get("source") == CONTACT_REACTIVE_STATUS_APPLICATION_SOURCE and (condition.get("side"), condition.get("slot_index"), condition.get("pokemon_id"), condition.get("payload", {}).get("condition")) == (attacker["side"], attacker["slot_index"], attacker["pokemon_id"], _ABILITIES.get(ability))
    if not _execution_matches(execution, attacker, move, turn) or not hp_ok or (outcome == "activation" and not condition_ok) or (outcome == "no_activation" and condition is not None): return _result("rejected", "incomplete_or_conflicting_observed_contact_receipt")
    committed = manager.capture_runtime_state_snapshot(receipt.get("session_id"))
    if committed.get("status") != "runtime_snapshot_ready": return _result("rejected", "runtime_snapshot_unavailable")
    return {"status":"resolved","reason":"idempotent_reuse","owner":deepcopy(defender),"observations":[deepcopy(receipt)],"runtime_snapshot":committed,"strategy_d0":freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=attacker),"idempotent":True}
def _payload(a,d,action,move,ability,outcome,before,after): return {"source_action_id":action,"move_id":move,"reactive_ability":ability,"outcome":outcome,"attacker_side":a["side"],"attacker_slot_index":a["slot_index"],"attacker_pokemon_id":a["pokemon_id"],"defender_side":d["side"],"defender_slot_index":d["slot_index"],"defender_pokemon_id":d["pokemon_id"],"hp_before":before,"hp_after":after}
def _receipt(snapshot, session, action):
    row=next((x for x in snapshot.get("ordered_observations",[]) if isinstance(x,Mapping) and x.get("observation_id")==f"{session}:contact-reactive:{action}:result"),None)
    return row if isinstance(row,Mapping) and row.get("event_kind")=="contact_reactive_status_result_observed" and row.get("payload",{}).get("source_action_id")==action else None
def _execution(snapshot,session,action):
    rows=[x for x in snapshot.get("ordered_observations",[]) if isinstance(x,Mapping) and x.get("session_id")==session and x.get("event_kind")=="executed_move_observed" and x.get("payload",{}).get("source_action_id")==action]
    return rows[0] if len(rows)==1 else ({} if rows else None)
def _execution_matches(row,owner,move,turn): return bool(row) and row.get("side")==owner["side"] and row.get("slot_index")==owner["slot_index"] and row.get("pokemon_id")==owner["pokemon_id"] and row.get("turn_number")==turn and row.get("payload",{}).get("move_id")==move
def _preview(snapshot,confirmations):
    if not isinstance(snapshot,Mapping) or snapshot.get("status")!="ready": return None
    return {**deepcopy(dict(snapshot)),"ordered_observations":sorted([*deepcopy(snapshot.get("ordered_observations",[])),*[deepcopy(x["observation"]) for x in confirmations]],key=lambda x:(x["observation_sequence"],x["observation_id"]))}
def _committed_ok(snapshot,a,d,after,ability,outcome,before_actor):
    state=snapshot.get("state") if isinstance(snapshot,Mapping) else None; target=_pokemon(state,d); actor=_pokemon(state,a)
    if not isinstance(target,Mapping) or target.get("pokemon_id") != d["pokemon_id"] or target.get("current_hp")!=after: return False
    if after == 0:
        if target.get("fainted") is not True: return False
    elif _active_owner(state,d["side"])!=d: return False
    if outcome=="activation": return isinstance(actor,Mapping) and actor.get("condition")==_ABILITIES[ability] and isinstance(actor.get("condition_provenance"),Mapping) and actor["condition_provenance"].get("event_kind") == "current_condition_observed"
    return isinstance(actor,Mapping) and isinstance(before_actor, Mapping) and actor.get("condition") == before_actor.get("condition") and actor.get("condition_provenance") == before_actor.get("condition_provenance")
def _active_owner(state,side):
    row=state.get(f"{side}_side") if isinstance(state,Mapping) else None; roster=row.get("pokemon") if isinstance(row,Mapping) else None; slot=row.get("active_slot_index") if isinstance(row,Mapping) else None; pokemon=roster.get(slot,roster.get(str(slot))) if isinstance(roster,Mapping) and isinstance(slot,int) and not isinstance(slot,bool) and slot>=0 else None; session=state.get("session_id") if isinstance(state,Mapping) else None
    return {"session_id":session,"side":side,"slot_index":slot,"pokemon_id":pokemon.get("pokemon_id")} if isinstance(session,str) and session and isinstance(pokemon,Mapping) and isinstance(pokemon.get("pokemon_id"),str) and pokemon.get("pokemon_id") and pokemon.get("fainted") is not True else None
def _pokemon(state,owner):
    side=state.get(f"{owner['side']}_side") if isinstance(state,Mapping) else None; roster=side.get("pokemon") if isinstance(side,Mapping) else None
    return roster.get(owner["slot_index"],roster.get(str(owner["slot_index"]))) if isinstance(roster,Mapping) else None
def _other(side): return "opponent" if side=="self" else "self"
def _token(value): return isinstance(value,str) and bool(value) and value==value.lower() and " " not in value and "_" not in value
def _positive(value): return isinstance(value,int) and not isinstance(value,bool) and value>0
def _nonnegative(value): return isinstance(value,int) and not isinstance(value,bool) and value>=0
def _result(status,reason): return {"status":status,"reason":reason,"owner":None,"observations":[],"runtime_snapshot":None,"strategy_d0":None,"idempotent":False}
