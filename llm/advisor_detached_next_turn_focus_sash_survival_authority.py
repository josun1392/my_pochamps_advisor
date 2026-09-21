"""Detached Focus Sash readiness and path-local single-hit consequence."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_detached_next_turn_held_item_effect_applicability import _base as _predictive_base, _owner, materialize_detached_next_turn_held_item_effect_applicability, validate_detached_next_turn_held_item_effect_applicability

SCHEMA_VERSION="detached-next-turn-focus-sash-survival-authority-v1"
CONSEQUENCE_SCHEMA_VERSION="detached-next-turn-focus-sash-consequence-v1"

def materialize_detached_next_turn_focus_sash_survival_authority(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,predictive_mechanics:Mapping[str,Any],holder:Mapping[str,Any],attacker:Mapping[str,Any],action:Mapping[str,Any],move_metadata:Mapping[str,Any],held_item_effect_applicability:Mapping[str,Any]|None=None,pair_local_predictive_mechanics:Mapping[str,Any]|None=None)->dict[str,Any]:
    if not _owner(holder) or not _owner(attacker) or holder["side"]==attacker["side"]: return _result("rejected","focus_sash_owner_identity_invalid",{})
    base=_predictive_base(next_decision_state,next_decision_fingerprint,predictive_mechanics,holder)
    if isinstance(base,str): return _result("rejected",base,{})
    if pair_local_predictive_mechanics is not None:
        from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import validate_detached_next_turn_pair_local_predictive_mechanics
        if validate_detached_next_turn_pair_local_predictive_mechanics(authority=pair_local_predictive_mechanics,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _result("rejected","pair_local_predictive_mechanics_invalid",{})
        rows=pair_local_predictive_mechanics.get("sides",{})
        if rows.get(holder["side"],{}).get("owner")!=dict(holder) or rows.get(attacker["side"],{}).get("owner")!=dict(attacker):return _result("rejected","pair_local_owner_identity_mismatch",{})
        base["row"],base["other_row"]=rows[holder["side"]],rows[attacker["side"]]
    if predictive_mechanics.get("active_owners",{}).get(attacker["side"])!=dict(attacker) or not isinstance(action,Mapping) or action.get("action_type")!="attack" or not isinstance(action.get("action_id"),str) or not isinstance(move_metadata,Mapping) or action.get("identity",action.get("move_id"))!=move_metadata.get("move_id"): return _result("rejected","focus_sash_action_or_identity_mismatch",{})
    row=base["row"]; item=row.get("item",{}); hp=row.get("current_hp",{}); common={"session_id":holder["session_id"],"source_next_decision_fingerprint":next_decision_fingerprint,"holder":deepcopy(dict(holder)),"attacker":deepcopy(dict(attacker)),"continuation_action_id":action["action_id"],"move_id":move_metadata.get("move_id"),"raw_current_item":deepcopy(dict(item)) if isinstance(item,Mapping) else {"status":"unknown"},"current_hp":hp.get("current_hp"),"maximum_hp":hp.get("maximum_hp"),"predictive_mechanics_authority":deepcopy(dict(predictive_mechanics))}
    if not isinstance(item,Mapping) or item.get("status")=="unknown": return _result("incomplete","focus_sash_item_unknown",common)
    if item.get("status")!="known" or item.get("value")!="focus-sash": return _ready("resolved","known_non_focus_sash_item",common,"known_no_effect",False,False)
    expected=materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,holder=holder,pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    auth=held_item_effect_applicability if held_item_effect_applicability is not None else expected
    if validate_detached_next_turn_held_item_effect_applicability(authority=auth,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,holder=holder,pair_local_predictive_mechanics=pair_local_predictive_mechanics) is not None: return _result("rejected","focus_sash_held_item_effect_authority_invalid",common)
    common["held_item_effect_applicability_authority"]=deepcopy(dict(auth))
    if auth.get("status")!="resolved": return _result("incomplete","focus_sash_item_effect_applicability_unavailable",common)
    if auth.get("effective_item_id")!="focus-sash" or auth.get("item_effects_active") is not True: return _ready("resolved","focus_sash_item_effects_suppressed",common,"known_no_effect",False,False)
    cur,maxhp=hp.get("current_hp"),hp.get("maximum_hp")
    if not isinstance(cur,int) or not isinstance(maxhp,int) or maxhp<=0 or not 0<=cur<=maxhp: return _result("incomplete","focus_sash_hp_unknown",common)
    if cur!=maxhp or cur<1:return _ready("resolved","hp_not_full",common,"known_no_effect",True,False)
    return _ready("ready",None,common,"available",True,True)

def apply_detached_focus_sash_single_hit(*,authority:Mapping[str,Any],damage:int,source_action_id:str|None=None,source_hit_id:str|None=None)->dict[str,Any]:
    if not isinstance(authority,Mapping) or authority.get("schema_version")!=SCHEMA_VERSION or authority.get("status") not in {"ready","resolved"}: return {"status":"rejected","reason":"focus_sash_authority_invalid"}
    if not isinstance(damage,int) or isinstance(damage,bool) or damage<0:return {"status":"rejected","reason":"focus_sash_damage_invalid"}
    hp=authority.get("current_hp"); lethal=authority.get("status")=="ready" and damage>=hp
    if not lethal:return {"status":"resolved","schema_version":CONSEQUENCE_SCHEMA_VERSION,"outcome":"not_activated","actual_damage":damage,"final_hp":max(0,hp-damage) if isinstance(hp,int) else None,"item_consumed":False,"source_authority":deepcopy(dict(authority)),"source_action_id":source_action_id,"source_hit_id":source_hit_id}
    return {"status":"resolved","schema_version":CONSEQUENCE_SCHEMA_VERSION,"outcome":"activated","actual_damage":max(0,hp-1),"final_hp":1,"item_before":"focus-sash","item_after":{"status":"known_absent","value":None},"item_consumed":True,"source_authority":deepcopy(dict(authority)),"source_action_id":source_action_id or authority.get("continuation_action_id"),"source_hit_id":source_hit_id,"provenance":"detached_focus_sash_path_local_single_hit_v1"}
def validate_detached_next_turn_focus_sash_survival_authority(*,authority:Any,**kwargs:Any)->str|None:
    expected=materialize_detached_next_turn_focus_sash_survival_authority(**kwargs)
    return None if isinstance(authority,Mapping) and deepcopy(dict(authority))==expected else "detached_focus_sash_survival_authority_mismatch"
def _ready(status,reason,base,outcome,available,eligible):return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"outcome":outcome,"focus_sash_available":available,"eligible":eligible,"reason":reason,"provenance":"detached_next_turn_focus_sash_survival_authority_v1"}
def _result(status,reason,base):return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
