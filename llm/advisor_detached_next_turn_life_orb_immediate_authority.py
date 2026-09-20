"""Detached authority for Life Orb's effective item and post-hit recoil."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.damage.move_categories import has_secondary_effect
from llm.advisor_detached_next_turn_held_item_effect_applicability import _base as _predictive_base, _owner, materialize_detached_next_turn_held_item_effect_applicability, validate_detached_next_turn_held_item_effect_applicability

SCHEMA_VERSION="detached-next-turn-life-orb-immediate-authority-v1"

def materialize_detached_next_turn_life_orb_immediate_authority(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,predictive_mechanics:Mapping[str,Any],attacker:Mapping[str,Any],target:Mapping[str,Any],action:Mapping[str,Any],move_metadata:Mapping[str,Any],qualifying_damage:bool,held_item_effect_applicability:Mapping[str,Any]|None=None)->dict[str,Any]:
    if not isinstance(qualifying_damage,bool):return _result("rejected","life_orb_qualifying_damage_invalid",{})
    if not _owner(attacker) or not _owner(target) or attacker["side"]==target["side"]:return _result("rejected","life_orb_owner_identity_invalid",{})
    base=_predictive_base(next_decision_state,next_decision_fingerprint,predictive_mechanics,attacker)
    if isinstance(base,str):return _result("rejected",base,{})
    if predictive_mechanics.get("active_owners",{}).get(target["side"])!=dict(target) or not isinstance(action,Mapping) or action.get("action_type")!="attack" or not isinstance(action.get("action_id"),str) or not isinstance(move_metadata,Mapping) or action.get("identity",action.get("move_id"))!=move_metadata.get("move_id"):return _result("rejected","life_orb_action_or_identity_mismatch",{})
    row,targetrow=base["row"],base["other_row"]; hp=row.get("current_hp",{}); item=row.get("item",{}); ability=row.get("ability",{}); target_ability=targetrow.get("ability",{})
    common={"session_id":attacker["session_id"],"source_next_decision_fingerprint":next_decision_fingerprint,"attacker":deepcopy(dict(attacker)),"target":deepcopy(dict(target)),"continuation_action_id":action["action_id"],"move_id":move_metadata.get("move_id"),"qualifying_damage":qualifying_damage,"raw_current_item":deepcopy(dict(item)) if isinstance(item,Mapping) else {"status":"unknown"},"attacker_ability":deepcopy(dict(ability)) if isinstance(ability,Mapping) else {"status":"unknown"},"target_ability":deepcopy(dict(target_ability)) if isinstance(target_ability,Mapping) else {"status":"unknown"},"current_hp":hp.get("current_hp"),"maximum_hp":hp.get("maximum_hp"),"predictive_mechanics_authority":deepcopy(dict(predictive_mechanics))}
    if not isinstance(item,Mapping) or item.get("status")=="unknown":return _result("incomplete","life_orb_item_unknown",common)
    expected=materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,holder=attacker)
    held=held_item_effect_applicability if held_item_effect_applicability is not None else expected
    if validate_detached_next_turn_held_item_effect_applicability(authority=held,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,holder=attacker) is not None:return _result("rejected","life_orb_held_item_effect_authority_invalid",common)
    common["held_item_effect_applicability_authority"]=deepcopy(dict(held))
    if held.get("status")!="resolved":return _result("incomplete","life_orb_item_effect_applicability_unavailable",common)
    effective="life-orb" if held.get("effective_item_id")=="life-orb" else None
    common["effective_item_id"]=effective
    if effective is None:return _resolved(common,"known_no_effect",0,None,False)
    cur,maxhp=hp.get("current_hp"),hp.get("maximum_hp")
    if not isinstance(cur,int) or not isinstance(maxhp,int) or maxhp<=0 or not 0<=cur<=maxhp:return _result("incomplete","life_orb_attacker_hp_unknown",common)
    if not isinstance(ability,Mapping) or ability.get("status")!="known" or not isinstance(target_ability,Mapping) or target_ability.get("status")!="known":return _result("incomplete","life_orb_relevant_ability_unknown",common)
    gas=target_ability.get("value")=="neutralizing-gas"; own=ability.get("value")
    if own=="magic-guard" and not gas:return _resolved(common,"recoil_suppressed",0,"magic-guard",qualifying_damage)
    if own=="sheer-force" and not gas and has_secondary_effect(move_metadata["move_id"]):return _resolved(common,"recoil_suppressed",0,"sheer-force",qualifying_damage)
    if not qualifying_damage:return _resolved(common,"not_triggered",0,None,False)
    recoil=max(1,maxhp//10);return _resolved(common,"recoiled",recoil,None,True)

def validate_detached_next_turn_life_orb_immediate_authority(*,authority:Any,**kwargs:Any)->str|None:
    expected=materialize_detached_next_turn_life_orb_immediate_authority(**kwargs)
    return None if isinstance(authority,Mapping) and deepcopy(dict(authority))==expected else "detached_life_orb_immediate_authority_mismatch"

def _resolved(base,outcome,recoil,suppressed,eligible):
    hp=base.get("current_hp"); maximum=base.get("maximum_hp"); post=max(0,hp-recoil) if isinstance(hp,int) else None
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"outcome":outcome,"damage_modifier":{"applies":base.get("effective_item_id")=="life-orb","effective_item_id":base.get("effective_item_id")},"recoil":{"eligible":eligible,"damage_fraction":{"numerator":1,"denominator":10},"rounding":"floor_minimum_one_when_applicable","pre_hp":hp,"max_hp":maximum,"recoil_damage":recoil,"post_hp":post,"fainted":post==0,"suppressed_by":suppressed},"provenance":"detached_next_turn_life_orb_immediate_authority_v1"}
def _result(status,reason,base):return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
