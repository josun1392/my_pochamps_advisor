"""Detached, conditional action-order authority for two next-turn intents."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping
from llm.narrow_action_order import evaluate_action_order
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_next_turn_predictive_mechanics_authority import validate_next_turn_predictive_mechanics_authority
from llm.advisor_detached_next_turn_held_item_effect_applicability import materialize_detached_next_turn_held_item_effect_applicability

SCHEMA_VERSION="detached-next-turn-action-order-authority-v1"

def materialize_detached_next_turn_action_order_authority(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,predictive_mechanics:Mapping[str,Any],action_intents:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(next_decision_state,Mapping) or fingerprint_transition_preview_state(next_decision_state)!=next_decision_fingerprint:return _result("rejected","stale_or_invalid_next_decision_fingerprint")
    if validate_next_turn_predictive_mechanics_authority(authority=predictive_mechanics,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _result("rejected","next_turn_predictive_mechanics_authority_invalid")
    intents=action_intents.get("intents") if isinstance(action_intents,Mapping) else None
    if not isinstance(intents,Mapping) or any(not isinstance(intents.get(side),Mapping) or intents[side].get("status")!="resolved" for side in ("self","opponent")):return _result("incomplete","next_turn_action_intents_unavailable")
    rows=predictive_mechanics.get("sides",{}); selfrow,opprow=rows.get("self"),rows.get("opponent")
    if not isinstance(selfrow,Mapping) or not isinstance(opprow,Mapping) or intents["self"].get("actor")!=selfrow.get("owner") or intents["opponent"].get("actor")!=opprow.get("owner"):return _result("rejected","next_turn_action_order_intent_identity_mismatch")
    items={side:materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=predictive_mechanics,holder=intents[side]["actor"]) for side in ("self","opponent")}
    if any(value.get("status")!="resolved" for value in items.values()):return _result("incomplete","next_turn_action_order_item_effect_applicability_unavailable")
    facts=_facts(next_decision_state,selfrow,opprow,items)
    if isinstance(facts,str):return _result("incomplete",facts)
    engine=evaluate_action_order(self_action=_move(intents["self"]),opponent_action=_move(intents["opponent"]),**facts)
    status={"acts_first":"resolved","acts_second":"resolved","speed_tie":"resolved","insufficient_context":"incomplete","unsupported_mechanic":"unsupported"}.get(engine.get("status"),"rejected")
    order={"acts_first":"self_first","acts_second":"opponent_first","speed_tie":"equal_speed_tie"}.get(engine.get("status"))
    result={"status":status,"schema_version":SCHEMA_VERSION,"source_next_decision_fingerprint":next_decision_fingerprint,"self_action_intent":deepcopy(dict(intents["self"])),"opponent_action_intent":deepcopy(dict(intents["opponent"])),"self_actor":deepcopy(dict(intents["self"]["actor"])),"opponent_actor":deepcopy(dict(intents["opponent"]["actor"])),"order_input_authority":facts,"held_item_effect_applicability_authorities":items,"order_engine":engine,"order":order,"provenance":"detached_next_turn_narrow_action_order_adapter_v1"}
    if status!="resolved":result["reason"]=engine.get("unsupported_reason") or (engine.get("missing_inputs") or ["detached_order_incomplete"])[0]
    else:result["order_branch_plan"]=_branches(result)
    return result

def validate_detached_next_turn_action_order_authority(*,authority:Any,**kwargs:Any)->str|None:
    expected=materialize_detached_next_turn_action_order_authority(**kwargs)
    return None if isinstance(authority,Mapping) and deepcopy(dict(authority))==expected else "detached_next_turn_action_order_authority_mismatch"

def _move(intent):
    metadata=intent["canonical_move_metadata_authority"];return {"move_id":intent["move_id"],"priority":metadata["priority"],"category":metadata["category"],"type":metadata["type"],"triage_healing":metadata.get("triage_healing","omitted")}
def _facts(state,s,o,items):
    def speed(row):return row.get("current_final_stats",{}).get("values",{}).get("speed")
    def stage(row):return row.get("current_stages",{}).get("values",{}).get("speed")
    def ability(row):return row.get("ability",{}).get("value") if row.get("ability",{}).get("status")=="known" else "unknown"
    def paralysis(row):
        c=row.get("condition",{});return "paralyzed" if c.get("status")=="known_present" and c.get("condition")=="paralysis" else "not_paralyzed" if c.get("status") in {"known_none","known_present"} else "unknown"
    def full(row):
        hp=row.get("current_hp",{});return "full" if hp.get("current_hp")==hp.get("maximum_hp") else "not_full" if isinstance(hp.get("current_hp"),int) and isinstance(hp.get("maximum_hp"),int) else "unknown"
    field=state.get("field",{}) if isinstance(state.get("field"),Mapping) else {}
    trick=_observed(field,"trick_room_status"); tailself=_observed(state.get("self_side",{}),"tailwind_status"); tailopp=_observed(state.get("opponent_side",{}),"tailwind_status")
    return {"self_final_speed":speed(s),"opponent_final_speed":speed(o),"self_speed_stage":stage(s),"opponent_speed_stage":stage(o),"self_paralysis":paralysis(s),"opponent_paralysis":paralysis(o),"self_speed_item":items["self"].get("effective_item_id"),"opponent_speed_item":items["opponent"].get("effective_item_id"),"self_speed_ability":ability(s),"opponent_speed_ability":ability(o),"self_priority_ability":ability(s),"opponent_priority_ability":ability(o),"self_gale_wings_full_hp":full(s),"opponent_gale_wings_full_hp":full(o),"weather":s.get("field",{}).get("weather","unknown"),"terrain":s.get("field",{}).get("terrain","unknown"),"trick_room":trick,"trick_room_provenance":"trusted_observed_current","self_tailwind":tailself,"opponent_tailwind":tailopp,"self_tailwind_provenance":"trusted_observed_current","opponent_tailwind_provenance":"trusted_observed_current","self_paralysis_provenance":"trusted_observed_current","opponent_paralysis_provenance":"trusted_observed_current","self_grounded":s.get("direct_mechanics",{}).get("combatant",{}).get("grounded","unknown"),"opponent_grounded":o.get("direct_mechanics",{}).get("combatant",{}).get("grounded","unknown")}
def _observed(row,key):
    value=row.get(key) if isinstance(row,Mapping) else None; provenance=row.get(f"{key}_provenance") if isinstance(row,Mapping) else None
    return value if value in {"active","inactive"} and isinstance(provenance,Mapping) and provenance.get("trust")=="user_confirmed_observation" else "unknown"
def _branches(authority):
    if authority["order"]=="self_first":return ({"branch_id":"deterministic:self_first","order":"self_first","conditional_probability":{"numerator":1,"denominator":1},"mechanic":"deterministic_order","source_action_order_authority":deepcopy(dict(authority))},)
    if authority["order"]=="opponent_first":return ({"branch_id":"deterministic:opponent_first","order":"opponent_first","conditional_probability":{"numerator":1,"denominator":1},"mechanic":"deterministic_order","source_action_order_authority":deepcopy(dict(authority))},)
    return tuple({"branch_id":f"equal_speed:{order}","order":order,"conditional_probability":{"numerator":1,"denominator":2},"mechanic":"equal_speed","source_action_order_authority":deepcopy(dict(authority))} for order in ("self_first","opponent_first"))
def _result(status,reason):return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
