"""Production admission for explicit Taunt, Encore, and Disable lifecycle facts."""
from copy import deepcopy
from typing import Mapping
from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, RESTRICTION_SOURCE, USER_TRUST
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager

_APPLICATION = {"taunt": "taunt_restriction_applied_observed", "encore": "encore_restriction_applied_observed", "disable": "disable_restriction_applied_observed"}
_COMPLETION = {"taunt": "taunt_restricted_turn_completed_observed", "encore": "encore_restricted_turn_completed_observed", "disable": "disable_restricted_turn_completed_observed"}

def admit_action_restriction_observation(*, runtime_session_manager, captured_session_id, side, restriction, operation, source_action_id=None, turn_number=None):
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager) or restriction not in _APPLICATION or operation not in {"applied", "completed"}: return _result("rejected", "invalid_restriction_request")
    snapshot=runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready": return _result("rejected", "runtime_snapshot_unavailable")
    owner=_owner(snapshot.get("state"),side)
    if owner is None or not isinstance(turn_number,int) or isinstance(turn_number,bool) or turn_number < 1: return _result("rejected", "active_owner_or_turn_invalid")
    payload={"completion_kind":"affected_active_turn_completed"}
    kind=_COMPLETION[restriction]
    if operation == "applied":
        if not isinstance(source_action_id,str) or not source_action_id: return _result("rejected", "source_action_invalid")
        kind=_APPLICATION[restriction]; payload={"source_action_id":source_action_id,"source_move_id":restriction}
        if restriction in {"encore","disable"}:
            history=_pokemon(snapshot["state"],owner).get("last_executed_move")
            if not isinstance(history,Mapping) or history.get("owner") != owner: return _result("incomplete", "last_executed_move_missing")
            move, execution=history.get("move_id"),history.get("execution_id")
            if not isinstance(move,str) or not move or not isinstance(execution,str) or not execution: return _result("rejected", "last_executed_move_invalid")
            payload[("locked_move_id" if restriction=="encore" else "disabled_move_id")]=move; payload["last_used_execution_id"]=execution
    allocated=runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status")!="allocated": return _result("rejected", "sequence_unavailable")
    sequence=allocated["observation_sequence"]; boundary=LifecycleConfirmationBoundary(captured_session_id,{side:owner})
    confirmed=boundary.confirm(event_kind=kind,payload=payload,session_id=captured_session_id,source=RESTRICTION_SOURCE,trust=USER_TRUST,confirmed=True,side=side,slot_index=owner["slot_index"],pokemon_id=owner["pokemon_id"],observation_id=f"{captured_session_id}:{restriction}:{operation}:{sequence}",turn_number=turn_number)
    if confirmed.get("status")!="confirmed": return _result("rejected",confirmed.get("excluded_reason","confirmation_rejected"))
    confirmed["observation"]["observation_sequence"]=sequence; rows=runtime_session_manager.read_collection_snapshot()["ordered_observations"]+[confirmed["observation"]]
    preview=runtime_session_manager.preview(captured_session_id,{"status":"ready","session_id":captured_session_id,"ordered_observations":sorted(rows,key=lambda x:(x["observation_sequence"],x["observation_id"]))})
    if preview.get("status")!="preview_ready": return _result("rejected","reducer_preview_rejected")
    admitted=runtime_session_manager.admit_confirmation(captured_session_id,confirmed)
    if admitted.get("status") not in {"added","duplicate"}: return _result("rejected","admission_rejected")
    applied=runtime_session_manager.apply(captured_session_id,runtime_session_manager.read_collection_snapshot())
    return {"status":"resolved","reason":None,"observation":deepcopy(confirmed["observation"])} if applied.get("status") in {"applied","already_applied"} else _result("rejected","application_rejected")

def _owner(state,side):
    area=state.get(f"{side}_side") if isinstance(state,Mapping) else None; slot=area.get("active_slot_index") if isinstance(area,Mapping) else None; p=_pokemon(state,{"side":side,"slot_index":slot})
    return {"session_id":state.get("session_id"),"side":side,"slot_index":slot,"pokemon_id":p.get("pokemon_id")} if side in {"self","opponent"} and isinstance(p,Mapping) and p.get("fainted") is not True else None
def _pokemon(state,owner):
    area=state.get(f"{owner.get('side')}_side") if isinstance(state,Mapping) else None; rows=area.get("pokemon") if isinstance(area,Mapping) else None; return rows.get(owner.get("slot_index")) if isinstance(rows,Mapping) else None
def _result(status,reason): return {"status":status,"reason":reason,"observation":None}
