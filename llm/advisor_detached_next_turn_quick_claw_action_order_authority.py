"""Detached Quick Claw branch plan conditional on authenticated action order."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping
from llm.advisor_detached_next_turn_action_order_authority import validate_detached_next_turn_action_order_authority

SCHEMA_VERSION="detached-next-turn-quick-claw-action-order-authority-v1"
def materialize_detached_next_turn_quick_claw_action_order_authority(*,action_order_authority:Mapping[str,Any],next_decision_state:Mapping[str,Any]|None=None,next_decision_fingerprint:str|None=None,predictive_mechanics:Mapping[str,Any]|None=None,action_intents:Mapping[str,Any]|None=None)->dict[str,Any]:
    if next_decision_state is None or next_decision_fingerprint is None:return {"status":"rejected","schema_version":SCHEMA_VERSION,"reason":"detached_action_order_validation_context_missing"}
    error=validate_detached_next_turn_action_order_authority(authority=action_order_authority,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,action_intents=action_intents)
    if error is not None:return {"status":"rejected","schema_version":SCHEMA_VERSION,"reason":error}
    if not isinstance(action_order_authority,Mapping) or action_order_authority.get("status")!="resolved":return {"status":"rejected","schema_version":SCHEMA_VERSION,"reason":"detached_action_order_authority_invalid"}
    items=action_order_authority.get("held_item_effect_applicability_authorities",{}); selfqc=items.get("self",{}).get("effective_item_id")=="quick-claw"; oppqc=items.get("opponent",{}).get("effective_item_id")=="quick-claw"
    base={"source_next_decision_fingerprint":action_order_authority.get("source_next_decision_fingerprint"),"source_action_order_authority":deepcopy(dict(action_order_authority))}
    if selfqc and oppqc:return {"status":"unsupported","schema_version":SCHEMA_VERSION,**base,"reason":"simultaneous_quick_claw_trigger_precedence_unowned"}
    if not selfqc and not oppqc:return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"known_no_effect","order_branches":deepcopy(action_order_authority.get("order_branch_plan",()))}
    priorities=action_order_authority.get("order_engine",{}); holder="self" if selfqc else "opponent"
    if priorities.get("self_priority")!=priorities.get("opponent_priority"):return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"known_no_effect","reason":"quick_claw_cannot_cross_priority_bracket","order_branches":deepcopy(action_order_authority.get("order_branch_plan",()))}
    holder_order=f"{holder}_first"; normal=action_order_authority.get("order")
    branches=[_branch(holder_order,holder,"activated",Fraction(1,5))]
    if normal in {"self_first","opponent_first"}:branches.append(_branch(normal,holder,"not_activated",Fraction(4,5)))
    elif normal=="equal_speed_tie":branches.extend(_branch(x["order"],holder,"not_activated",Fraction(2,5)) for x in action_order_authority.get("order_branch_plan",()))
    else:return {"status":"rejected","schema_version":SCHEMA_VERSION,**base,"reason":"quick_claw_non_activation_order_invalid"}
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"applicable","holder":holder,"activation_probability":{"numerator":1,"denominator":5},"non_activation_probability":{"numerator":4,"denominator":5},"order_branches":tuple(branches),"probability_semantics":"mechanical_quick_claw_conditional_on_selected_actions"}
def validate_detached_next_turn_quick_claw_action_order_authority(*,authority:Any,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,**kwargs:Any)->str|None:
    if not isinstance(authority,Mapping):return "detached_next_turn_quick_claw_authority_invalid"
    source=kwargs.get("action_order_authority",authority.get("source_action_order_authority"))
    expected=materialize_detached_next_turn_quick_claw_action_order_authority(action_order_authority=source,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=kwargs.get("predictive_mechanics") or (source.get("predictive_mechanics_authority") if isinstance(source,Mapping) else None),action_intents=kwargs.get("action_intents") or (source.get("action_intents_authority") if isinstance(source,Mapping) else None))
    return None if deepcopy(dict(authority))==expected else "detached_next_turn_quick_claw_authority_mismatch"
def _branch(order,holder,state,p):return {"branch_id":f"quick_claw:{holder}:{state}:{order}","order":order,"mechanic":"quick_claw","quick_claw_activation":state,"conditional_probability":{"numerator":p.numerator,"denominator":p.denominator}}
