"""Single authenticated hypothetical ordinary-attack ledger at next decision.

The attack mechanics are deliberately shared with the detached standard-charge
turn-two executor.  This module only authenticates an ordinary hypothetical
intent and supplies its bounded normal-formula move descriptor; it never
orders or composes two actions.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_next_turn_predictive_mechanics_authority import validate_next_turn_predictive_mechanics_authority
from llm.advisor_detached_next_turn_action_intent import validate_detached_next_turn_action_intents
from llm.advisor_detached_standard_charge_turn_two_attack_execution import _execute_one

AUTHORITY_SCHEMA_VERSION="detached-next-turn-ordinary-attack-execution-authority-v1"
SCHEMA_VERSION="detached-next-turn-ordinary-attack-execution-v1"

def materialize_detached_next_turn_ordinary_attack_execution_authority(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,predictive_mechanics:Mapping[str,Any],action_intents:Mapping[str,Any],side:str)->dict[str,Any]:
    if side not in {"self","opponent"}:return _result("rejected","ordinary_attack_side_invalid")
    if not isinstance(next_decision_state,Mapping) or not isinstance(next_decision_fingerprint,str) or fingerprint_transition_preview_state(next_decision_state)!=next_decision_fingerprint:return _result("rejected","stale_or_invalid_next_decision_fingerprint")
    if validate_next_turn_predictive_mechanics_authority(authority=predictive_mechanics,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _result("rejected","next_turn_predictive_mechanics_authority_invalid")
    error=validate_detached_next_turn_action_intents(authority=action_intents,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint)
    if error is not None:return _result("rejected",error)
    intent=action_intents.get("intents",{}).get(side); other="opponent" if side=="self" else "self"
    if not isinstance(intent,Mapping) or intent.get("action_origin")!="hypothetical_selected_action":return _result("rejected","ordinary_executor_requires_hypothetical_action_intent")
    actor,target=predictive_mechanics.get("sides",{}).get(side),predictive_mechanics.get("sides",{}).get(other)
    if not isinstance(actor,Mapping) or not isinstance(target,Mapping) or intent.get("actor")!=actor.get("owner") or intent.get("target")!=target.get("owner"):return _result("rejected","ordinary_attack_intent_predictive_identity_mismatch")
    move=_move(intent.get("canonical_move_metadata_authority"),intent.get("move_id"))
    if isinstance(move,str):return _result("unsupported",move)
    secondary=_secondary(move)
    if isinstance(secondary,str):return _result("unsupported",secondary)
    row={"status":"resolved","schema_version":AUTHORITY_SCHEMA_VERSION,"side":side,"source_next_decision_fingerprint":next_decision_fingerprint,"actor":deepcopy(dict(intent["actor"])),"target":deepcopy(dict(intent["target"])),"move_id":intent["move_id"],"continuation_action_id":intent["action_id"],"canonical_terminal_effect":{"move":move,"secondary":secondary},"predictive_actor_mechanics":deepcopy(dict(actor)),"predictive_target_mechanics":deepcopy(dict(target)),"action_intent":deepcopy(dict(intent)),"execution_grant":"authenticated_hypothetical_ordinary_attack_only"}
    return {"status":"resolved","schema_version":AUTHORITY_SCHEMA_VERSION,"source_next_decision_fingerprint":next_decision_fingerprint,"next_decision_state":deepcopy(dict(next_decision_state)),"predictive_mechanics":deepcopy(dict(predictive_mechanics)),"action_intents":deepcopy(dict(action_intents)),"side":side,"action":row,"provenance":"detached_next_turn_hypothetical_ordinary_attack_authority_v1"}

def validate_detached_next_turn_ordinary_attack_execution_authority(*,authority:Any,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,**kwargs:Any)->str|None:
    if not isinstance(authority,Mapping):return "ordinary_attack_execution_authority_invalid"
    expected=materialize_detached_next_turn_ordinary_attack_execution_authority(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=kwargs.get("predictive_mechanics",authority.get("predictive_mechanics")),action_intents=kwargs.get("action_intents",authority.get("action_intents")),side=kwargs.get("side",authority.get("side")))
    return None if deepcopy(dict(authority))==expected else "ordinary_attack_execution_authority_mismatch"

def execute_detached_next_turn_ordinary_attack(*,execution_authority:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(execution_authority,Mapping) or execution_authority.get("status")!="resolved" or execution_authority.get("schema_version")!=AUTHORITY_SCHEMA_VERSION:return _result("rejected","ordinary_attack_execution_authority_invalid")
    error=validate_detached_next_turn_ordinary_attack_execution_authority(authority=execution_authority,next_decision_state=execution_authority.get("next_decision_state"),next_decision_fingerprint=execution_authority.get("source_next_decision_fingerprint"))
    if error is not None:return _result("rejected",error)
    # The shared kernel consumes precisely these detached sources for item,
    # survival, secondary, and recoil authorities.
    kernel={"next_decision_state":execution_authority["next_decision_state"],"source_next_decision_fingerprint":execution_authority["source_next_decision_fingerprint"],"predictive_mechanics":execution_authority["predictive_mechanics"]}
    result=_execute_one(execution_authority["action"],kernel)
    return {"status":result.get("status"),"schema_version":SCHEMA_VERSION,"source_next_decision_fingerprint":execution_authority["source_next_decision_fingerprint"],"execution_authority":deepcopy(dict(execution_authority)),"action_ledger":result,"provenance":"detached_next_turn_ordinary_attack_ledger_v1"}

def validate_detached_next_turn_ordinary_attack_execution(*,result:Any,execution_authority:Mapping[str,Any])->str|None:
    """Strictly replay one ordinary detached ledger; embedded provenance is insufficient."""
    expected=execute_detached_next_turn_ordinary_attack(execution_authority=execution_authority)
    return None if isinstance(result,Mapping) and deepcopy(dict(result))==expected else "detached_next_turn_ordinary_attack_execution_mismatch"

def _move(metadata:Any,move_id:Any)->dict[str,Any]|str:
    if not isinstance(metadata,Mapping) or metadata.get("status")!="resolved" or metadata.get("move_id",move_id)!=move_id:return "ordinary_attack_metadata_invalid"
    value=metadata.get("metadata") if isinstance(metadata.get("metadata"),Mapping) else metadata
    if value.get("category") not in {"physical","special"} or not isinstance(value.get("power"),int) or isinstance(value["power"],bool) or value["power"]<=0:return "ordinary_attack_non_normal_formula_family_unsupported"
    if not isinstance(value.get("accuracy"),int) or isinstance(value["accuracy"],bool) or not 1<=value["accuracy"]<=100:return "ordinary_attack_accuracy_unsupported"
    if value.get("min_hits",1)!=1 or value.get("max_hits",1)!=1 or value.get("charge") is True or value.get("drain") or value.get("recoil"):return "ordinary_attack_special_family_unsupported"
    if value.get("stat_changes") not in (None, [], ()) :return "ordinary_attack_secondary_unowned"
    if not isinstance(value.get("type"),str) or not value["type"] or not isinstance(value.get("priority"),int):return "ordinary_attack_metadata_invalid"
    return {"move_id":move_id,"power":value["power"],"accuracy":value["accuracy"],"category":value["category"],"type":value["type"],"priority":value["priority"],"target":value.get("target"),"effect_chance":value.get("effect_chance"),"ailment":value.get("ailment","none")}
def _secondary(move):
    ailment,chance=move.get("ailment"),move.get("effect_chance")
    if ailment in {None,"none"} and chance in {None,0}:return {"kind":"none"}
    if not isinstance(chance,int) or isinstance(chance,bool) or not 1<=chance<=99:return "ordinary_attack_secondary_metadata_invalid"
    if ailment=="flinch":return {"kind":"flinch","chance":chance}
    if ailment in {"paralysis","burn"}:return {"kind":"status","condition":ailment,"chance":chance}
    return "ordinary_attack_secondary_unowned"
def _result(status,reason):return {"status":status,"schema_version":AUTHORITY_SCHEMA_VERSION,"reason":reason}
