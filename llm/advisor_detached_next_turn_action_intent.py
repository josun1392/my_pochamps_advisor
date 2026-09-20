"""Authenticated conditional next-turn action intents; never an execution grant."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation

SCHEMA_VERSION="detached-next-turn-action-intent-authority-v1"
SET_SCHEMA_VERSION="detached-next-turn-action-intent-set-v1"
_SIDES=("self","opponent")

def materialize_detached_next_turn_action_intents(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,hypothetical_actions:Mapping[str,Any]|None=None,forced_continuation:Mapping[str,Any]|None=None)->dict[str,Any]:
    if not isinstance(next_decision_state,Mapping) or not isinstance(next_decision_fingerprint,str) or fingerprint_transition_preview_state(next_decision_state)!=next_decision_fingerprint:return _result("rejected","stale_or_invalid_next_decision_fingerprint")
    forced=forced_continuation or materialize_detached_standard_charge_forced_continuation(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint)
    if not isinstance(forced,Mapping) or forced.get("status")!="resolved":return _result(forced.get("status","rejected"),forced.get("reason","forced_continuation_unavailable"))
    supplied=hypothetical_actions or {}; rows={}
    for side in _SIDES:
        owner=next_decision_state.get("active",{}).get(side); target=next_decision_state.get("active",{}).get("opponent" if side=="self" else "self")
        source=forced.get("forced_continuation_actions",{}).get(side)
        if not isinstance(owner,Mapping) or not isinstance(target,Mapping):return _result("rejected","next_turn_action_intent_active_identity_invalid")
        if isinstance(source,Mapping) and source.get("status")=="resolved":
            if side in supplied:return _result("rejected","forced_continuation_action_intent_conflict")
            metadata=source.get("canonical_move_metadata_authority") or source.get("move_metadata_authority")
            if isinstance(metadata, Mapping) and isinstance(metadata.get("metadata"), Mapping):
                metadata={"status":"resolved", **deepcopy(dict(metadata["metadata"]))}
            if not isinstance(metadata,Mapping): metadata={"status":"resolved","move_id":source.get("move_id"),"priority":0,"category":source.get("category"),"type":source.get("type"),"triage_healing":"omitted"}
            rows[side]=_row(next_decision_fingerprint,owner,target,source.get("continuation_action_id"),source.get("move_id"),metadata,"forced_standard_charge_continuation",source)
        else:
            value=supplied.get(side)
            if value is None:return _result("incomplete",f"{side}_next_turn_action_intent_missing")
            if not isinstance(value,Mapping) or value.get("actor")!=owner or value.get("target")!=target:return _result("rejected","hypothetical_action_intent_identity_mismatch")
            rows[side]=_row(next_decision_fingerprint,owner,target,value.get("action_id"),value.get("move_id"),value.get("canonical_move_metadata_authority"),"hypothetical_selected_action",value)
        if isinstance(rows[side],str):return _result("rejected",rows[side])
    return {"status":"resolved","schema_version":SET_SCHEMA_VERSION,"source_next_decision_fingerprint":next_decision_fingerprint,"forced_continuation":deepcopy(dict(forced)),"intents":rows,"provenance":"detached_next_turn_action_intent_set_v1"}

def validate_detached_next_turn_action_intents(*,authority:Any,**kwargs:Any)->str|None:
    expected=materialize_detached_next_turn_action_intents(**kwargs)
    return None if isinstance(authority,Mapping) and deepcopy(dict(authority))==expected else "detached_next_turn_action_intent_authority_mismatch"

def _row(fp,actor,target,action_id,move_id,metadata,origin,source):
    if isinstance(metadata, Mapping) and isinstance(metadata.get("metadata"), Mapping): metadata={"status":"resolved", **deepcopy(dict(metadata["metadata"]))}
    if not isinstance(action_id,str) or not action_id or not isinstance(move_id,str) or not move_id or not isinstance(metadata,Mapping) or metadata.get("status")!="resolved" or metadata.get("move_id",move_id)!=move_id:return "next_turn_action_intent_metadata_invalid"
    needed=("priority","category","type")
    if any(key not in metadata for key in needed):return "next_turn_action_intent_order_metadata_incomplete"
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"source_next_decision_fingerprint":fp,"actor":deepcopy(dict(actor)),"target":deepcopy(dict(target)),"action_id":action_id,"move_id":move_id,"action_origin":origin,"canonical_move_metadata_authority":deepcopy(dict(metadata)),"action_selection_probability":"not_modeled" if origin=="hypothetical_selected_action" else "not_applicable","source_forced_continuation":deepcopy(dict(source)) if origin.startswith("forced") else None,"execution_grant":False,"provenance":"detached_next_turn_hypothetical_action_intent_v1" if origin.startswith("hypothetical") else "detached_next_turn_forced_continuation_action_intent_v1"}
def _result(status,reason):return {"status":status,"schema_version":SET_SCHEMA_VERSION,"reason":reason}
