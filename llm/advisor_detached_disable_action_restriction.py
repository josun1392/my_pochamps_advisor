"""Disable application, future selectability, and pending execution gate."""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
SCHEMA_VERSION="detached-disable-action-restriction-v1"
_B=("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner")

def materialize_detached_disable_application(*,strategy_d0,action,actor,target,accuracy_authority,last_used_move_authority,current_known_moves_authority,current_disable_authority,target_side_ability_authority,protection_authority,reflection_authority):
    base=_base(strategy_d0,action,actor,target)
    if base is None:return _result("rejected","disable_application_binding_invalid",{})
    for v,n in ((accuracy_authority,"accuracy"),(target_side_ability_authority,"target_side_ability"),(protection_authority,"protection"),(reflection_authority,"reflection")):
        bad=_bound(v,base,n,actor,target)
        if bad:return _result(*bad,base)
    if accuracy_authority.get("outcome")=="missed":return _out(base,"missed","disable_missed",accuracy_authority)
    if accuracy_authority.get("outcome")!="hit":return _result("rejected","disable_accuracy_outcome_invalid",base)
    if protection_authority.get("outcome")=="blocked":return _out(base,"blocked","disable_blocked_by_protection",protection_authority)
    if protection_authority.get("outcome")!="not_applicable":return _result("rejected","disable_protection_outcome_invalid",base)
    if reflection_authority.get("outcome")=="reflected":return _result("incomplete","disable_reflection_execution_unsupported",base)
    if reflection_authority.get("outcome")!="not_applicable":return _result("rejected","disable_reflection_outcome_invalid",base)
    if target_side_ability_authority.get("ability")=="aroma-veil":return _out(base,"canonical_failure","disable_target_protected_by_aroma_veil",target_side_ability_authority)
    if not _owner_bound(current_disable_authority,base,target):return _result("incomplete","current_disable_authority_missing",base)
    if current_disable_authority.get("state")=="active":return _out(base,"canonical_failure","disable_target_already_disabled",current_disable_authority)
    if current_disable_authority.get("state")!="not_active":return _result("rejected","current_disable_state_invalid",base)
    if not _owner_bound(last_used_move_authority,base,target):return _out(base,"canonical_failure","disable_target_last_executed_move_missing",last_used_move_authority if isinstance(last_used_move_authority,Mapping) else {})
    move=last_used_move_authority.get("move_id")
    if not isinstance(move,str) or not move:return _result("rejected","disable_last_executed_move_invalid",base)
    if not _owner_bound(current_known_moves_authority,base,target):return _result("incomplete","disable_current_known_moves_authority_missing",base)
    moves=current_known_moves_authority.get("move_ids")
    if not isinstance(moves,list) or any(not isinstance(x,str) or not x for x in moves):return _result("incomplete","disable_current_known_moves_incomplete",base)
    if move not in moves:return _out(base,"canonical_failure","disable_target_no_longer_knows_last_move",current_known_moves_authority,disabled_move_id=move)
    return _out(base,"applicable","disable_applicable",accuracy_authority,disabled_move_id=move,last_used_execution_id=last_used_move_authority.get("execution_id"),remaining_target_turns=4)

def materialize_disable_execution_gate(*,selected_action,actor,current_restriction=None,same_branch_application=None):
    meta=selected_action.get("metadata_authority",selected_action.get("move_metadata_authority")) if isinstance(selected_action,Mapping) else None; m=meta.get("metadata") if isinstance(meta,Mapping) else None
    if not isinstance(m,Mapping) or not isinstance(m.get("move_id"),str) or not m["move_id"]:return _result("incomplete","selected_action_move_metadata_unknown",{})
    src=[x for x in (current_restriction,same_branch_application) if x is not None]
    if not src:return _result("incomplete","disable_restriction_authority_missing",{})
    disabled=[]
    for x in src:
        if not isinstance(x,Mapping) or x.get("owner",x.get("target"))!=dict(actor):return _result("rejected","disable_restriction_actor_binding_mismatch",{})
        if x.get("status")!="resolved":return _result(x.get("status","rejected"),x.get("reason","disable_restriction_unavailable"),{})
        if x.get("state")=="active" or x.get("outcome")=="applicable":disabled.append(x.get("disabled_move_id"))
    restricted=m["move_id"] in disabled
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"actor":deepcopy(dict(actor)),"selected_action_id":selected_action.get("action_id"),"selected_move_id":m["move_id"],"execution_state":"restricted_by_disable" if restricted else "executable","reason":"disable_restricts_selected_move" if restricted else "disable_does_not_restrict_selected_move","restriction_evidence":tuple(deepcopy(x) for x in src),"provenance":"selected_intent_preserved_disable_execution_gate_v1"}

def resolve_disable_move_selectability(*,disable_authority,owner,move_metadata_authority):
    m=move_metadata_authority.get("metadata") if isinstance(move_metadata_authority,Mapping) else None
    if not isinstance(m,Mapping) or not isinstance(m.get("move_id"),str) or not m["move_id"]:return _result("incomplete","disable_move_metadata_missing",{})
    if not isinstance(disable_authority,Mapping) or disable_authority.get("status")!="resolved" or disable_authority.get("owner")!=dict(owner):return _result("incomplete","current_disable_authority_missing",{})
    if disable_authority.get("state") not in {"active","not_active"}:return _result("rejected","current_disable_state_invalid",{})
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"owner":deepcopy(dict(owner)),"move_id":m["move_id"],"selectability":"not_selectable" if disable_authority["state"]=="active" and m["move_id"]==disable_authority.get("disabled_move_id") else "selectable","reason":"disable_restricts_move" if disable_authority["state"]=="active" and m["move_id"]==disable_authority.get("disabled_move_id") else "disable_does_not_restrict_move"}

def disable_restriction_failure_leaf(*,strategy_d0,action,actor,target,gate):
    active=strategy_d0.get("strategy_state",{}).get("active",{}); own=active.get(actor.get("side"),{}).get("current_hp"); foe=active.get(target.get("side"),{}).get("current_hp")
    if not all(isinstance(x,int) and not isinstance(x,bool) and x>=0 for x in (own,foe)) or gate.get("status")!="resolved" or gate.get("execution_state")!="restricted_by_disable":return _result("rejected","disable_failure_gate_or_hp_invalid",{})
    leaf={"leaf_id":f"{action['action_id']}:disable_restricted","candidate_id":action["action_id"],"action_type":action.get("action_type","attack"),"branch_path":("action_restriction","disable"),"probability":{"numerator":1,"denominator":1},"hit_state":"not_applicable","critical_state":"not_applicable","damage_roll":"not_applicable","consequences":{"damage":0,"own_final_hp":own,"target_final_hp":foe,"target_ko":foe==0,"self_fainted":own==0,"secondary":None,"contact":"not_applicable","execution_failure":"disable_action_restriction","disable_execution_gate":deepcopy(dict(gate))},"provenance":{"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(dict(strategy_d0["decision_owner"])),"attacker":deepcopy(dict(actor)),"target":deepcopy(dict(target)),"move_id":gate["selected_move_id"],"disable_action_restriction":deepcopy(dict(gate))}}
    return {"status":"evaluable","terminal_leaves":(leaf,),"terminal_probability_mass":{"numerator":1,"denominator":1}}

def _base(d,a,actor,target):
    meta=a.get("metadata_authority",a.get("move_metadata_authority")) if isinstance(a,Mapping) else None;m=meta.get("metadata") if isinstance(meta,Mapping) else None
    if not isinstance(d,Mapping) or d.get("status")!="resolved" or d.get("active_owners",{}).get(actor.get("side") if isinstance(actor,Mapping) else None)!=dict(actor) or d.get("active_owners",{}).get(target.get("side") if isinstance(target,Mapping) else None)!=dict(target) or not isinstance(m,Mapping) or any(m.get(k)!=v for k,v in {"move_id":"disable","category":"status","type":"normal","accuracy":100,"priority":0}.items()):return None
    return {"session_id":d["session_id"],"source_runtime_fingerprint":d["source_runtime_fingerprint"],"source_branch_fingerprint":d["strategy_preview_fingerprint"],"decision_owner":deepcopy(dict(d["decision_owner"])),"actor":deepcopy(dict(actor)),"target":deepcopy(dict(target)),"action_id":a.get("action_id"),"move_id":"disable"}
def _bound(v,b,n,actor,target):
    if not isinstance(v,Mapping):return("incomplete",f"disable_{n}_authority_missing")
    if v.get("status")!="resolved":return(v.get("status","rejected"),v.get("reason",f"disable_{n}_authority_unavailable"))
    return None if all(v.get(k)==b.get(k) for k in _B) and v.get("actor")==dict(actor) and v.get("target")==dict(target) and v.get("action_id")==b["action_id"] and v.get("move_id")=="disable" else("rejected",f"disable_{n}_authority_binding_mismatch")
def _owner_bound(v,b,o):return isinstance(v,Mapping) and v.get("status")=="resolved" and v.get("owner")==dict(o) and all(v.get(k)==b.get(k) for k in _B)
def _out(b,outcome,reason,a,**x):return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(b)),"outcome":outcome,"reason":reason,**deepcopy(x),"authority":deepcopy(dict(a)),"provenance":"strict_detached_disable_application_v1"}
def _result(status,reason,base):return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
