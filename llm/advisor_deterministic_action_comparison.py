"""Pure pairwise comparison of already-materialized detached outcomes.

This deliberately does not feed the legacy recommendation ranking.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_substitute import substitute_state
from llm.advisor_bind_residual import bind_state
from llm.advisor_perish_song import perish_state

SCHEMA="deterministic-action-comparison-v1"; KEYS=("session_id","side","slot_index","pokemon_id")

def compare_candidates(*, decision_owner:Mapping[str,Any], candidate_a:Mapping[str,Any], candidate_b:Mapping[str,Any])->dict[str,Any]:
    a=_normalize(decision_owner,candidate_a); b=_normalize(decision_owner,candidate_b)
    if a.get("status")!="resolved" or b.get("status")!="resolved": return {"status":"incomplete","reason":"insufficient_comparable_authority","candidates":{"a":a,"b":b}}
    if a["session_id"]!=b["session_id"] or a["source_branch_fingerprint"]!=b["source_branch_fingerprint"]: return _result("rejected","mismatched_candidate_decision_branch")
    for fact, reason, prefer in (("own_fainted","avoids_self_ko",False),("opponent_fainted","causes_opponent_ko",True)):
        if a[fact]!=b[fact]: return _preferred("a" if a[fact] is prefer else "b",reason,a,b)
    if not a["own_fainted"] and a["own_hp"]!=b["own_hp"]: return _preferred("a" if a["own_hp"]>b["own_hp"] else "b","safer_exact_self_hp",a,b)
    return {"status":"resolved","comparison":"tied_on_supported_facts","reason":"supported_terminal_and_hp_facts_tie","facts":{"a":a,"b":b}}

def _normalize(decision_owner:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    if not _owner(decision_owner) or not isinstance(candidate,Mapping) or candidate.get("schema_version")!="deterministic-candidate-outcome-v1" or candidate.get("completeness")!="complete": return _result("incomplete","candidate_outcome_incomplete")
    state=candidate.get("outcome_state"); fp=candidate.get("outcome_branch_fingerprint")
    if not isinstance(state,Mapping) or fingerprint_transition_preview_state(state)!=fp or not isinstance(candidate.get("candidate_id"),str) or candidate.get("action_type") not in {"attack","manual_switch"} or not isinstance(candidate.get("source_branch_fingerprint"),str): return _result("rejected","invalid_candidate_outcome_authority")
    active=state.get("active"); own=active.get(decision_owner["side"]) if isinstance(active,Mapping) else None; other="opponent" if decision_owner["side"]=="self" else "self"; foe=active.get(other) if isinstance(active,Mapping) else None
    owner_matches = _same_side_owner(own, decision_owner) if candidate.get("action_type") == "manual_switch" else _same(own, decision_owner)
    if not owner_matches or not _active(own) or not _active(foe): return _result("rejected","foreign_or_invalid_decision_owner")
    own_id={k:own[k] for k in KEYS}; foe_id={k:foe[k] for k in KEYS}
    return {"status":"resolved","candidate_id":candidate["candidate_id"],"action_type":candidate["action_type"],"session_id":decision_owner["session_id"],"source_branch_fingerprint":candidate["source_branch_fingerprint"],"own_fainted":own["fainted"],"opponent_fainted":foe["fainted"],"own_hp":own["current_hp"],"opponent_hp":foe["current_hp"],"switch_completed":candidate["action_type"]=="manual_switch","substitute":substitute_state(state,own_id),"bind":bind_state(state,own_id),"perish_song":perish_state(state,own_id)}
def _preferred(which:str,reason:str,a:Mapping[str,Any],b:Mapping[str,Any])->dict[str,Any]:return {"status":"resolved","comparison":"preferred","preferred_candidate":which,"reason":reason,"facts":{"a":deepcopy(dict(a)),"b":deepcopy(dict(b))}}
def _owner(x:Any)->bool:return isinstance(x,Mapping) and set(x)==set(KEYS) and isinstance(x.get("session_id"),str) and x.get("side") in {"self","opponent"} and isinstance(x.get("slot_index"),int) and isinstance(x.get("pokemon_id"),str)
def _same(x:Any,o:Mapping[str,Any])->bool:return isinstance(x,Mapping) and dict(o)=={k:x.get(k) for k in KEYS}
def _same_side_owner(x:Any,o:Mapping[str,Any])->bool:return isinstance(x,Mapping) and x.get("session_id")==o.get("session_id") and x.get("side")==o.get("side")
def _active(x:Any)->bool:return isinstance(x,Mapping) and isinstance(x.get("current_hp"),int) and isinstance(x.get("max_hp"),int) and x["max_hp"]>0 and 0<=x["current_hp"]<=x["max_hp"] and x.get("fainted") is (x["current_hp"]==0)
def _result(status:str,reason:str)->dict[str,Any]:return {"status":status,"reason":reason}
