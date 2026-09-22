"""Production admission for one observed Champions confusion action-gate result."""
from __future__ import annotations
from copy import deepcopy
import hashlib
from typing import Any, Mapping

from llm.advisor_champions_confusion_action_lifecycle_derived_observation import (
    CLEARED_DERIVED, PROGRESSION_DERIVED, derive_confusion_action_lifecycle_consequence,
)
from llm.advisor_champions_confusion_progression import valid_confusion_progression
from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate
from llm.advisor_detached_observed_rng_reconciliation import (
    reconcile_observed_confusion_action_gate_rng,
    retain_historical_confusion_action_gate,
)
from llm.advisor_lifecycle_confirmation import (
    EXECUTED_MOVE_SOURCE, LifecycleConfirmationBoundary,
    PENDING_CONFUSION_ACTION_EXECUTION_SOURCE, USER_TRUST,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0

_OUTCOMES={"confusion_self_hit","confusion_selected_action_executes","confusion_snaps_out_and_executes"}


def resolve_pending_confusion_action_identity(*, runtime_snapshot:Mapping[str,Any], side:str,
                                              move_id:str, turn_number:int,
                                              observation_snapshot:Mapping[str,Any] | None = None) -> dict[str,Any]:
    state=runtime_snapshot.get("state") if isinstance(runtime_snapshot,Mapping) else None
    owner,_pokemon=_active_owner(state,side)
    if (owner is None or not isinstance(move_id,str) or not move_id or move_id!=move_id.lower()
            or " " in move_id or "_" in move_id or not isinstance(turn_number,int)
            or isinstance(turn_number,bool) or turn_number<1):
        return {"status":"rejected","reason":"invalid_pending_confusion_action_identity"}
    existing=state.get("pending_confusion_action_execution_context") if isinstance(state,Mapping) else None
    provenance=existing.get("provenance") if isinstance(existing,Mapping) else None
    if (isinstance(existing,Mapping) and existing.get("actor")==owner and existing.get("move_id")==move_id
            and isinstance(provenance,Mapping) and provenance.get("turn_number")==turn_number
            and isinstance(existing.get("action_id"),str) and existing["action_id"]
            and isinstance(existing.get("decision_point"),str) and existing["decision_point"]):
        return {"status":"resolved","reason":"existing_pending_identity_reuse",
                "owner":deepcopy(owner),"action_id":existing["action_id"],
                "decision_point":existing["decision_point"]}
    compatible=[
        row for row in (observation_snapshot.get("ordered_observations", []) if isinstance(observation_snapshot,Mapping) else [])
        if isinstance(row,Mapping)
        and row.get("event_kind")=="executed_move_observed"
        and row.get("source")==EXECUTED_MOVE_SOURCE
        and row.get("trust")==USER_TRUST
        and row.get("session_id")==owner["session_id"] and row.get("turn_number")==turn_number
        and (row.get("side"),row.get("slot_index"),row.get("pokemon_id"))
        == (owner["side"],owner["slot_index"],owner["pokemon_id"])
        and row.get("payload",{}).get("move_id")==move_id
    ]
    if len(compatible)>1:
        return {"status":"rejected","reason":"ambiguous_pending_confusion_action_identity"}
    seed=f"{owner['session_id']}|{owner['side']}|{owner['slot_index']}|{owner['pokemon_id']}|{turn_number}|{move_id}|confusion"
    action_digest=hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    action_id=f"pending-confusion:{turn_number}:{owner['side']}:{move_id}:{action_digest}"
    if compatible:
        linked=compatible[0].get("payload",{}).get("source_action_id")
        if not isinstance(linked,str) or not linked:
            return {"status":"rejected","reason":"invalid_existing_pending_confusion_action_identity"}
        action_id=linked
    decision_seed=f"{owner['session_id']}|{owner['side']}|{owner['slot_index']}|{owner['pokemon_id']}|{turn_number}|pending-confusion"
    decision_digest=hashlib.sha256(decision_seed.encode("utf-8")).hexdigest()[:12]
    return {"status":"resolved","reason":"existing_execution_reuse" if compatible else "deterministic_pending_confusion_identity","owner":deepcopy(owner),
            "action_id":action_id,
            "decision_point":f"pending-confusion:{turn_number}:{owner['side']}:{decision_digest}"}


def admit_observed_confusion_action_result(*, runtime_session_manager:BattleObservationRuntimeSessionManager,
                                           captured_session_id:str, side:str, turn_number:int,
                                           move_id:str, outcome_class:str) -> dict[str,Any]:
    snapshot=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    identity=resolve_pending_confusion_action_identity(
        runtime_snapshot=snapshot,side=side,move_id=move_id,turn_number=turn_number,
        observation_snapshot=runtime_session_manager.read_collection_snapshot())
    if identity.get("status")!="resolved":
        return _result(identity.get("status","rejected"),identity.get("reason","pending_confusion_identity_rejected"))
    owner=identity["owner"]
    return admit_pending_confusion_action_execution(
        runtime_session_manager=runtime_session_manager,captured_session_id=captured_session_id,
        side=owner["side"],slot_index=owner["slot_index"],pokemon_id=owner["pokemon_id"],
        turn_number=turn_number,decision_point=identity["decision_point"],action_id=identity["action_id"],
        move_id=move_id,outcome_class=outcome_class)


def admit_pending_confusion_action_execution(*, runtime_session_manager:BattleObservationRuntimeSessionManager,
                                             captured_session_id:str, side:str, slot_index:int, pokemon_id:str,
                                             turn_number:int, decision_point:str, action_id:str, move_id:str,
                                             outcome_class:str) -> dict[str,Any]:
    if not isinstance(runtime_session_manager,BattleObservationRuntimeSessionManager):
        return _result("rejected","invalid_runtime_manager")
    snapshot=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    state=snapshot.get("state") if snapshot.get("status")=="runtime_snapshot_ready" else None
    owner,pokemon=_active_owner(state,side)
    if owner is None or owner.get("slot_index")!=slot_index or owner.get("pokemon_id")!=pokemon_id:
        return _result("rejected","pending_confusion_action_actor_mismatch")
    if outcome_class not in _OUTCOMES:
        return _result("rejected","unsupported_confusion_action_outcome")
    prior_context=state.get("pending_confusion_action_execution_context") if isinstance(state,Mapping) else None
    same_identity=(isinstance(prior_context,Mapping) and prior_context.get("actor")==owner and all(
        prior_context.get(key)==value for key,value in {
            "decision_point":decision_point,"action_id":action_id,"move_id":move_id,
        }.items()))
    if same_identity and prior_context.get("outcome_class")!=outcome_class:
        return _result("rejected","conflicting_pending_confusion_action_retry")
    if same_identity:
        return {"status":"resolved","reason":"duplicate_pending_confusion_action","runtime_committed":False,
                "observation":None,"derived_observations":[],"runtime_snapshot":deepcopy(snapshot),
                "strategy_d0":freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=owner),
                "retained_prediction":None,"rng_reconciliation":None}
    if pokemon.get("current_confusion")!="confused":
        return _result("rejected","pending_confusion_action_state_mismatch")
    progression=pokemon.get("champions_confusion_progression")
    if not valid_confusion_progression(progression,owner):
        return _result("incomplete","champions_confusion_progression_unavailable")
    pre_d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=owner)
    if pre_d0.get("status")!="resolved":
        return _result("incomplete","confusion_pre_action_d0_unavailable")
    gate=freeze_champions_confusion_action_gate(
        strategy_d0=pre_d0,runtime_snapshot=snapshot,actor=owner,action_id=action_id,move_id=move_id,
        action_order={"decision_point":decision_point},path=())
    if gate.get("status")!="resolved":
        return _result(gate.get("status","incomplete"),gate.get("reason","confusion_gate_unavailable"))
    retained=retain_historical_confusion_action_gate(
        predictive_gate=gate,turn_number=turn_number,decision_point=decision_point)
    if retained.get("status")!="resolved":
        return _result("rejected",retained.get("reason","confusion_gate_retention_rejected"))
    seq=runtime_session_manager.allocate_observation_sequence()
    if seq.get("status")!="allocated" or seq.get("session_id")!=captured_session_id:
        return _result("rejected","observation_sequence_binding_mismatch")
    boundary=LifecycleConfirmationBoundary(captured_session_id,{side:owner})
    confirmation=boundary.confirm(
        event_kind="pending_confusion_action_execution_observed",
        payload={"decision_point":decision_point,"action_id":action_id,"move_id":move_id,"outcome_class":outcome_class},
        session_id=captured_session_id,source=PENDING_CONFUSION_ACTION_EXECUTION_SOURCE,trust=USER_TRUST,
        confirmed=True,side=side,slot_index=slot_index,pokemon_id=pokemon_id,
        observation_id=f"{captured_session_id}:pending-confusion-action:{seq['observation_sequence']}",turn_number=turn_number)
    if confirmation.get("status")!="confirmed":
        return _result("rejected",confirmation.get("excluded_reason","pending_confusion_action_confirmation_rejected"))
    source=confirmation["observation"]; source["observation_sequence"]=seq["observation_sequence"]
    allocated=runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status")!="allocated": return _result("rejected","derived_sequence_unavailable")
    common={"decision_point":decision_point,"action_id":action_id,"move_id":move_id,"outcome_class":outcome_class}
    if outcome_class in {"confusion_self_hit","confusion_selected_action_executes"}:
        common.update(prior_opportunities_before=progression["prior_opportunities"],
                      prior_opportunities_after=progression["prior_opportunities"]+1)
        kind=PROGRESSION_DERIVED
    else:
        kind=CLEARED_DERIVED
    derived=derive_confusion_action_lifecycle_consequence(
        event_kind=kind,session_id=captured_session_id,turn_number=turn_number,
        observation_id=f"{captured_session_id}:confusion-lifecycle:{allocated['observation_sequence']}",
        observation_sequence=allocated["observation_sequence"],source_pending_observation=source,payload=common)
    if derived.get("status")!="confirmed": return _result("rejected",derived.get("reason"))
    confirmations=[confirmation,derived]
    rows=deepcopy(runtime_session_manager.read_collection_snapshot().get("ordered_observations",[]))
    rows.extend(deepcopy(row["observation"]) for row in confirmations)
    rows.sort(key=lambda row:(row.get("observation_sequence"),row.get("observation_id")))
    collection=runtime_session_manager.read_collection_snapshot()
    preview=runtime_session_manager.preview(captured_session_id,{**collection,"ordered_observations":rows})
    if preview.get("status")!="preview_ready": return _result("rejected","confusion_lifecycle_preview_rejected")
    admitted=runtime_session_manager.admit_confirmations_atomically(captured_session_id,confirmations)
    if admitted.get("status") not in {"added","duplicate"}: return _result("rejected","confusion_lifecycle_admission_rejected")
    applied=runtime_session_manager.apply(captured_session_id,runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied","already_applied"}: return _result("rejected","confusion_lifecycle_application_rejected")
    committed=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    d0=freeze_runtime_strategy_d0(runtime_snapshot=committed,decision_owner=owner) if committed.get("status")=="runtime_snapshot_ready" else {}
    reconciliation=reconcile_observed_confusion_action_gate_rng(
        retained_prediction=retained,pending_confusion_action_observation=source)
    return {"status":"resolved","reason":None,"runtime_committed":True,"observation":deepcopy(source),
            "derived_observations":[deepcopy(derived["observation"])],"runtime_snapshot":deepcopy(committed),
            "strategy_d0":d0 if d0.get("status")=="resolved" else None,
            "retained_prediction":deepcopy(retained),"rng_reconciliation":deepcopy(reconciliation)}

def _active_owner(state:Any,side:str):
    side_state=state.get(f"{side}_side") if isinstance(state,Mapping) else None
    roster=side_state.get("pokemon") if isinstance(side_state,Mapping) else None
    slot=side_state.get("active_slot_index") if isinstance(side_state,Mapping) else None
    pokemon=roster.get(slot,roster.get(str(slot))) if isinstance(roster,Mapping) and isinstance(slot,int) else None
    if not isinstance(pokemon,Mapping) or not isinstance(state.get("session_id"),str): return None,None
    return {"session_id":state["session_id"],"side":side,"slot_index":slot,"pokemon_id":pokemon.get("pokemon_id")},pokemon

def _result(status,reason):
    return {"status":status,"reason":reason,"runtime_committed":False,"observation":None,
            "derived_observations":[],"runtime_snapshot":None,"strategy_d0":None,
            "retained_prediction":None,"rng_reconciliation":None}
