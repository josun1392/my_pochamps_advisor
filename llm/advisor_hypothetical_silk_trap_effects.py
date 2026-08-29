"""Strict detached Silk Trap blocked-contact Speed consequence."""
from copy import deepcopy
from typing import Any,Mapping
from advisor.canonical_silk_trap_reactive_protection import canonical_silk_trap_metadata, canonical_kings_shield_metadata, canonical_obstruct_metadata
from advisor.canonical_spiky_shield_reactive_damage import canonical_spiky_shield_reactive_damage_metadata
from advisor.canonical_baneful_bunker_reactive_poison import canonical_baneful_bunker_reactive_poison_metadata
from llm.advisor_hypothetical_protection_effects import project_self_protection

def project_silk_trap_protection(*,branch_state,action,owner,success_authority):
 meta=canonical_silk_trap_metadata(action.get("move",{}).get("move_id") if isinstance(action,Mapping) else None)
 if meta is None:return {"status":"unsupported","reason":"canonical_silk_trap_metadata"}
 proxy={"owner":deepcopy(dict(owner)),"move":{"move_id":"protect","category":action["move"].get("category"),"target":action["move"].get("target"),"accuracy":action["move"].get("accuracy")}}
 result=project_self_protection(branch_state=branch_state,action=proxy,expected_owner=owner,success_authority=success_authority)
 if result.get("status")!="resolved":return result
 return {**result,"metadata":meta,"provenance":"canonical_silk_trap_shared_ordinary_protection_v1"}

def project_kings_shield_protection(*,branch_state,action,owner,success_authority):
 meta=canonical_kings_shield_metadata(action.get("move",{}).get("move_id") if isinstance(action,Mapping) else None)
 if meta is None:return {"status":"unsupported","reason":"canonical_kings_shield_metadata"}
 proxy={"owner":deepcopy(dict(owner)),"move":{"move_id":"protect","category":action["move"].get("category"),"target":action["move"].get("target"),"accuracy":action["move"].get("accuracy")}}
 result=project_self_protection(branch_state=branch_state,action=proxy,expected_owner=owner,success_authority=success_authority)
 if result.get("status")!="resolved":return result
 return {**result,"metadata":meta,"provenance":"canonical_kings_shield_shared_ordinary_protection_v1"}

def project_obstruct_protection(*,branch_state,action,owner,success_authority):
 meta=canonical_obstruct_metadata(action.get("move",{}).get("move_id") if isinstance(action,Mapping) else None)
 if meta is None:return {"status":"unsupported","reason":"canonical_obstruct_metadata"}
 proxy={"owner":deepcopy(dict(owner)),"move":{"move_id":"protect","category":action["move"].get("category"),"target":action["move"].get("target"),"accuracy":action["move"].get("accuracy")}}
 result=project_self_protection(branch_state=branch_state,action=proxy,expected_owner=owner,success_authority=success_authority)
 if result.get("status")!="resolved":return result
 return {**result,"metadata":meta,"provenance":"canonical_obstruct_shared_ordinary_protection_v1"}

def project_spiky_shield_protection(*,branch_state,action,owner,success_authority):
 meta=canonical_spiky_shield_reactive_damage_metadata(action.get("move",{}).get("move_id") if isinstance(action,Mapping) else None)
 if meta is None:return {"status":"unsupported","reason":"canonical_spiky_shield_metadata"}
 proxy={"owner":deepcopy(dict(owner)),"move":{"move_id":"protect","category":action["move"].get("category"),"target":action["move"].get("target"),"accuracy":action["move"].get("accuracy")}}
 result=project_self_protection(branch_state=branch_state,action=proxy,expected_owner=owner,success_authority=success_authority)
 if result.get("status")!="resolved":return result
 return {**result,"metadata":meta,"provenance":"canonical_spiky_shield_shared_ordinary_protection_v1"}

def project_baneful_bunker_protection(*,branch_state,action,owner,success_authority):
 meta=canonical_baneful_bunker_reactive_poison_metadata(action.get("move",{}).get("move_id") if isinstance(action,Mapping) else None)
 if meta is None:return {"status":"unsupported","reason":"canonical_baneful_bunker_metadata"}
 proxy={"owner":deepcopy(dict(owner)),"move":{"move_id":"protect","category":action["move"].get("category"),"target":action["move"].get("target"),"accuracy":action["move"].get("accuracy")}}
 result=project_self_protection(branch_state=branch_state,action=proxy,expected_owner=owner,success_authority=success_authority)
 if result.get("status")!="resolved":return result
 return {**result,"metadata":meta,"provenance":"canonical_baneful_bunker_shared_ordinary_protection_v1"}

def resolve_silk_trap_speed_effect(*,strategy_d0,runtime_snapshot,blocked_action,blocked_attacker,shield_owner,contact_authority,reactive_interaction_authority):
 if not isinstance(contact_authority,Mapping):return {"status":"incomplete","reason":"silk_trap_contact_authority_missing"}
 required={"session_id":strategy_d0.get("session_id"),"source_runtime_fingerprint":strategy_d0.get("source_runtime_fingerprint"),"source_branch_fingerprint":strategy_d0.get("strategy_preview_fingerprint"),"decision_owner":strategy_d0.get("decision_owner"),"action_id":blocked_action.get("action_id"),"attacker":blocked_attacker,"target":shield_owner,"move_id":blocked_action.get("identity")}
 if any(contact_authority.get(k)!=v for k,v in required.items()):return {"status":"rejected","reason":"silk_trap_contact_authority_binding_mismatch"}
 if contact_authority.get("status")=="rejected":return {"status":"rejected","reason":contact_authority.get("reason","silk_trap_contact_authority_rejected")}
 if contact_authority.get("status")!="resolved":return {"status":"incomplete","reason":contact_authority.get("reason","silk_trap_contact_authority_unavailable")}
 if contact_authority.get("contact_state")=="non_contact":return {"status":"resolved","applies":False,"contact_authority":deepcopy(dict(contact_authority)),"provenance":"canonical_silk_trap_non_contact_no_effect_v1"}
 if contact_authority.get("contact_state")!="contact":return {"status":"rejected","reason":"silk_trap_contact_state_invalid"}
 if not isinstance(reactive_interaction_authority,Mapping):return {"status":"incomplete","reason":"silk_trap_reactive_interaction_authority_missing"}
 expected={"schema_version":"runtime-d0-silk-trap-speed-drop-interaction-authority-v1","session_id":strategy_d0.get("session_id"),"source_runtime_fingerprint":strategy_d0.get("source_runtime_fingerprint"),"source_branch_fingerprint":strategy_d0.get("strategy_preview_fingerprint"),"blocked_attacker":blocked_attacker,"shield_owner":shield_owner,"blocked_action_id":blocked_action.get("action_id"),"blocked_move_id":blocked_action.get("identity")}
 if any(reactive_interaction_authority.get(k)!=v for k,v in expected.items()):return {"status":"rejected","reason":"silk_trap_reactive_interaction_authority_binding_mismatch"}
 if reactive_interaction_authority.get("status")=="rejected":return {"status":"rejected","reason":reactive_interaction_authority.get("reason","silk_trap_reactive_interaction_authority_rejected")}
 if reactive_interaction_authority.get("status")!="resolved":return {"status":"incomplete","reason":reactive_interaction_authority.get("reason","silk_trap_reactive_interaction_authority_unavailable")}
 outcome=reactive_interaction_authority.get("outcome")
 before,after=reactive_interaction_authority.get("speed_stage_before"),reactive_interaction_authority.get("speed_stage_after")
 if outcome not in {"applies","prevented","reversed"} or not isinstance(before,int) or isinstance(before,bool) or not isinstance(after,int) or isinstance(after,bool) or not -6<=before<=6 or not -6<=after<=6:return {"status":"rejected","reason":"silk_trap_reactive_interaction_result_invalid"}
 return {
  "status":"resolved", "applies":outcome!="prevented",
  "contact_authority":deepcopy(dict(contact_authority)),
  "reactive_interaction_authority":deepcopy(dict(reactive_interaction_authority)),
  "stage_authority":deepcopy(dict(reactive_interaction_authority.get("stage_authority", {}))),
  "effect":{"owner":"blocked_attacker", "stat":"speed", "previous_stage":before,
            "requested_delta":-1, "resulting_stage":after, "interaction_outcome":outcome},
  "provenance":"canonical_silk_trap_blocked_contact_speed_drop_v1",
 }

def resolve_kings_shield_attack_effect(**kwargs):
 result=resolve_silk_trap_speed_effect(**kwargs)
 authority=kwargs.get("reactive_interaction_authority")
 if result.get("status")!="resolved" or result.get("applies") is not True:return result
 before=authority.get("attack_stage_before") if isinstance(authority,Mapping) else None
 after=authority.get("attack_stage_after") if isinstance(authority,Mapping) else None
 if not isinstance(before,int) or isinstance(before,bool) or not isinstance(after,int) or isinstance(after,bool) or not -6<=before<=6 or not -6<=after<=6:return {"status":"rejected","reason":"kings_shield_reactive_interaction_result_invalid"}
 result["effect"]={"owner":"blocked_attacker","stat":"attack","previous_stage":before,"requested_delta":-1,"resulting_stage":after,"interaction_outcome":authority.get("outcome")}
 result["provenance"]="canonical_kings_shield_blocked_contact_attack_drop_v1"
 return result

def resolve_obstruct_defense_effect(**kwargs):
 result=resolve_silk_trap_speed_effect(**kwargs)
 authority=kwargs.get("reactive_interaction_authority")
 if result.get("status")!="resolved" or result.get("applies") is not True:return result
 before=authority.get("defense_stage_before") if isinstance(authority,Mapping) else None
 after=authority.get("defense_stage_after") if isinstance(authority,Mapping) else None
 if not isinstance(before,int) or isinstance(before,bool) or not isinstance(after,int) or isinstance(after,bool) or not -6<=before<=6 or not -6<=after<=6:return {"status":"rejected","reason":"obstruct_reactive_interaction_result_invalid"}
 result["effect"]={"owner":"blocked_attacker","stat":"defense","previous_stage":before,"requested_delta":-2,"resulting_stage":after,"interaction_outcome":authority.get("outcome")}
 result["provenance"]="canonical_obstruct_blocked_contact_defense_drop_v1"
 return result
