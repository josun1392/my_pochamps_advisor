"""Exact observed Perish Song state; deliberately not a generic countdown engine."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_ice_body_end_of_turn import _owners, _sync_hp
from llm.advisor_transition_preview import fingerprint_transition_preview_state

_SCHEMA="detached-perish-song-state-v1"; _PROV="trusted_observed_perish_song_result_v1"; _KEYS=("session_id","side","slot_index","pokemon_id")
CANONICAL_PERISH_SONG_AUTHORITY={"source":"pokemon-showdown","move_source":"https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts#perishsong","initial_duration":4,"first_visible_count":3,"residual_order":24,"bypasses_substitute":True,"soundproof":"trusted_unaffected_owner","switch":"clears"}

def materialize_observed_perish_song(*, branch_state: Mapping[str,Any], source_branch_fingerprint:str, observed_result:Mapping[str,Any])->dict[str,Any]:
    if fingerprint_transition_preview_state(branch_state)!=source_branch_fingerprint or not _valid(observed_result,source_branch_fingerprint): return _result("rejected","stale_or_invalid_observed_perish_song_result")
    owners=_owners(branch_state); affected=observed_result["affected_owners"]
    if owners is None or {tuple(x.items()) for x in affected}-{tuple(x.items()) for x in owners.values()}: return _result("rejected","foreign_perish_song_owner")
    for owner in affected:
        if branch_state["active"][owner["side"]]["fainted"]: return _result("rejected","perish_song_fainted_owner")
        prior=perish_state(branch_state,owner)
        if prior["state"]=="unknown": return _result("incomplete","perish_song_state_unknown")
        if prior["state"]=="known_active": return _result("rejected","perish_song_already_active")
    state=deepcopy(dict(branch_state))
    for owner in affected:_set(state,owner,"known_active",4,source_branch_fingerprint)
    fp=fingerprint_transition_preview_state(state)
    return {"status":"resolved","source_branch_fingerprint":source_branch_fingerprint,"resulting_branch_fingerprint":fp,"next_state":state,"perish_song_application":{"affected_owners":deepcopy(affected),"initial_duration":4,"first_visible_count":3},"materialization":"pure_idempotent"} if fp else _result("rejected","unserializable_perish_song")

def perish_state(state:Mapping[str,Any],owner:Mapping[str,Any])->dict[str,Any]:
    context=state.get("perish_song_state_context") if isinstance(state,Mapping) else None
    if context is None:return {"state":"legacy_untracked"}
    if not isinstance(context,Mapping) or context.get("schema_version")!=_SCHEMA or context.get("session_id")!=owner.get("session_id") or context.get("provenance")!=_PROV or not isinstance(context.get("states"),list):return {"state":"unknown"}
    rows=[r for r in context["states"] if isinstance(r,Mapping) and r.get("owner")==dict(owner)]
    if len(rows)!=1:return {"state":"unknown"}
    r=rows[0]
    if r.get("state")=="known_active" and r.get("remaining_count") in {1,2,3,4}:return {"state":"known_active","remaining_count":r["remaining_count"]}
    if r.get("state") in {"known_inactive","unknown"} and r.get("remaining_count") is None:return {"state":r["state"]}
    return {"state":"unknown"}

def apply_owner_perish_song_end_of_turn(*,state:dict[str,Any],side:str,owner:Mapping[str,Any],source_branch_fingerprint:str)->dict[str,Any]:
    owners=_owners(state)
    if owners is None or owners.get(side)!=dict(owner) or fingerprint_transition_preview_state(state)!=source_branch_fingerprint:return _result("rejected","stale_or_foreign_perish_song_owner")
    row=perish_state(state,owner)
    if row["state"] in {"legacy_untracked","known_inactive"}:return {"status":"resolved","trace":None}
    if row["state"]=="unknown":return _result("incomplete","perish_song_state_unknown")
    active=state["active"][side]
    if active["fainted"]:_set(state,owner,"known_inactive",None,source_branch_fingerprint);return {"status":"resolved","trace":None}
    count=row["remaining_count"]-1
    if count:
        _set(state,owner,"known_active",count,source_branch_fingerprint);return {"status":"resolved","trace":{"effect":"perish_song","owner":deepcopy(dict(owner)),"count_before":row["remaining_count"],"count_after":count,"execution_status":"decremented"}}
    active["current_hp"],active["fainted"]=0,True;_sync_hp(state,side,0,active["max_hp"]);_set(state,owner,"known_inactive",None,source_branch_fingerprint)
    return {"status":"resolved","trace":{"effect":"perish_song","owner":deepcopy(dict(owner)),"count_before":1,"count_after":0,"terminal_faint":True,"execution_status":"fainted"}}

def apply_perish_song_residual_phase(*, branch_state: Mapping[str,Any], source_branch_fingerprint: str)->dict[str,Any]:
    """Atomically resolve all exact order-24 Perish owners; no side ordering is invented."""
    owners=_owners(branch_state)
    if owners is None or fingerprint_transition_preview_state(branch_state)!=source_branch_fingerprint:return _result("rejected","stale_or_invalid_perish_song_phase")
    rows=[]
    for owner in owners.values():
        row=perish_state(branch_state,owner)
        if row["state"]=="unknown":return _result("incomplete","perish_song_state_unknown")
        if row["state"]=="known_active": rows.append((owner,row))
    state=deepcopy(dict(branch_state)); trace=[]
    # Simultaneous expiry is one detached terminal mutation, not a synthetic side order.
    for owner,row in rows:
        side=owner["side"]; active=state["active"][side]
        if active["fainted"]: _set(state,owner,"known_inactive",None,source_branch_fingerprint); continue
        count=row["remaining_count"]-1
        if count:_set(state,owner,"known_active",count,source_branch_fingerprint); trace.append({"effect":"perish_song","owner":deepcopy(dict(owner)),"count_before":row["remaining_count"],"count_after":count,"execution_status":"decremented"})
        else: active["current_hp"],active["fainted"]=0,True;_sync_hp(state,side,0,active["max_hp"]);_set(state,owner,"known_inactive",None,source_branch_fingerprint);trace.append({"effect":"perish_song","owner":deepcopy(dict(owner)),"count_before":1,"count_after":0,"terminal_faint":True,"execution_status":"fainted"})
    fp=fingerprint_transition_preview_state(state)
    return {"status":"resolved","source_branch_fingerprint":source_branch_fingerprint,"resulting_branch_fingerprint":fp,"next_state":state,"trace":trace,"ordering":{"tier":24,"scope":"simultaneous_exact_owners"}} if fp else _result("rejected","unserializable_perish_song_phase")

def rebind_perish_song_after_switch(*,source_branch:Mapping[str,Any],state:dict[str,Any],outgoing_owner:Mapping[str,Any],incoming_owner:Mapping[str,Any],source_branch_fingerprint:str)->None:
    context=source_branch.get("perish_song_state_context")
    if context is None:return
    if not isinstance(context,Mapping):state["perish_song_state_context"]=context;return
    state["perish_song_state_context"]=deepcopy(dict(context));_set(state,outgoing_owner,"known_inactive",None,source_branch_fingerprint);_set(state,incoming_owner,"unknown",None,source_branch_fingerprint)

def _set(state:dict[str,Any],owner:Mapping[str,Any],status:str,count:int|None,fp:str)->None:
    c=state.get("perish_song_state_context")
    if not isinstance(c,dict) or c.get("schema_version")!=_SCHEMA or not isinstance(c.get("states"),list):c={"schema_version":_SCHEMA,"session_id":owner["session_id"],"source_branch_fingerprint":fp,"provenance":_PROV,"states":[]};state["perish_song_state_context"]=c
    c["states"][:]=[r for r in c["states"] if not(isinstance(r,Mapping) and r.get("owner")==dict(owner))];c["states"].append({"owner":deepcopy(dict(owner)),"state":status,"remaining_count":count})
def _owner(x:Any)->bool:return isinstance(x,Mapping) and set(x)==set(_KEYS) and isinstance(x.get("session_id"),str) and bool(x["session_id"]) and x.get("side") in {"self","opponent"} and isinstance(x.get("slot_index"),int) and not isinstance(x["slot_index"],bool) and x["slot_index"]>=0 and isinstance(x.get("pokemon_id"),str) and bool(x["pokemon_id"])
def _valid(x:Any,fp:str)->bool:return isinstance(x,Mapping) and set(x)=={"schema_version","session_id","source_branch_fingerprint","move_id","result","affected_owners","provenance"} and x.get("schema_version")=="observed-perish-song-result-v1" and x.get("move_id")=="perish-song" and x.get("result")=="applied" and x.get("source_branch_fingerprint")==fp and x.get("provenance")==_PROV and isinstance(x.get("affected_owners"),list) and x["affected_owners"] and all(_owner(o) and o["session_id"]==x.get("session_id") for o in x["affected_owners"])
def _result(status:str,reason:str)->dict[str,Any]:return {"status":status,"reason":reason}
