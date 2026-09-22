"""Strict derived lifecycle records for one observed confusion action opportunity."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

MECHANICS_DERIVED_TRUST = "mechanics_derived_runtime"
CHAMPIONS_CONFUSION_ACTION_LIFECYCLE_SOURCE = "runtime_champions_confusion_action_lifecycle_v1"
PROGRESSION_DERIVED = "champions_confusion_progression_derived"
CLEARED_DERIVED = "champions_confusion_cleared_derived"
DERIVED_KINDS = frozenset({PROGRESSION_DERIVED, CLEARED_DERIVED})

def derive_confusion_action_lifecycle_consequence(*, event_kind:str, session_id:str, turn_number:int,
                                                  observation_id:str, observation_sequence:int,
                                                  source_pending_observation:Mapping[str,Any],
                                                  payload:Mapping[str,Any]) -> dict[str,Any]:
    source=dict(source_pending_observation) if isinstance(source_pending_observation,Mapping) else {}
    data=deepcopy(dict(payload)) if isinstance(payload,Mapping) else {}
    if (event_kind not in DERIVED_KINDS or not _positive(turn_number) or not _positive(observation_sequence)
        or not isinstance(observation_id,str) or not observation_id
        or source.get("event_kind")!="pending_confusion_action_execution_observed"
        or source.get("session_id")!=session_id or source.get("turn_number")!=turn_number
        or not isinstance(source.get("observation_id"),str) or not source["observation_id"]
        or not _positive(source.get("observation_sequence")) or source["observation_sequence"]>=observation_sequence):
        return {"status":"rejected","reason":"invalid_pending_confusion_action_source"}
    data["source_pending_observation_id"]=source["observation_id"]
    if not _valid(event_kind,source,data):
        return {"status":"rejected","reason":"invalid_champions_confusion_lifecycle_payload"}
    return {"status":"confirmed","observation":{
        "event_kind":event_kind,"session_id":session_id,"turn_number":turn_number,
        "observation_id":observation_id,"observation_sequence":observation_sequence,
        "side":source.get("side"),"slot_index":source.get("slot_index"),"pokemon_id":source.get("pokemon_id"),
        "payload":data,"source":CHAMPIONS_CONFUSION_ACTION_LIFECYCLE_SOURCE,
        "trust":MECHANICS_DERIVED_TRUST,"scope":"champions_confusion_action_lifecycle",
        "reducer_eligibility":"candidate",
    }}

def _valid(kind,source,payload):
    sp=source.get("payload")
    if not isinstance(sp,Mapping): return False
    for key in ("decision_point","action_id","move_id","confusion_origin_id","outcome_class"):
        if payload.get(key)!=sp.get(key): return False
    if not isinstance(payload.get("confusion_origin_id"),str) or not payload["confusion_origin_id"]:
        return False
    outcome=payload.get("outcome_class")
    if kind==PROGRESSION_DERIVED:
        return (outcome in {"confusion_self_hit","confusion_selected_action_executes"}
                and isinstance(payload.get("prior_opportunities_before"),int)
                and payload.get("prior_opportunities_after")==payload["prior_opportunities_before"]+1)
    return outcome=="confusion_snaps_out_and_executes"

def _positive(value):
    return isinstance(value,int) and not isinstance(value,bool) and value>=1
