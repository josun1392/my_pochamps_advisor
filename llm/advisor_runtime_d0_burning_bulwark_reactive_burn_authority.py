"""Strict detached Burning Bulwark blocked-contact burn authority."""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from advisor.canonical_burning_bulwark_reactive_burn import canonical_burning_bulwark_reactive_burn_metadata
from llm.advisor_runtime_strategy_d0 import freeze_runtime_current_condition_authority,runtime_strategy_d0_freshness

SCHEMA_VERSION="runtime-d0-burning-bulwark-reactive-burn-authority-v1"
_OWNER=("session_id","side","slot_index","pokemon_id")
_CONDS={"burn","poison","toxic","paralysis","sleep","freeze"}
def build_burning_bulwark_successful_block_context(*,session_id:str,shield_owner:Mapping[str,Any],shield_action_id:str,blocked_attacker:Mapping[str,Any],blocked_action_id:str,blocked_move_id:str,protection_authority:Mapping[str,Any],action_blocked:bool,protection_bypass:bool,substitute_authority:Mapping[str,Any])->dict[str,Any]:
 shield,attacker=_owner(shield_owner),_owner(blocked_attacker)
 if not isinstance(session_id,str) or not session_id or shield["side"]==attacker["side"] or not all(isinstance(x,str) and x for x in (shield_action_id,blocked_action_id,blocked_move_id)) or not isinstance(action_blocked,bool) or not isinstance(protection_bypass,bool) or not _protection(protection_authority,shield) or not _substitute(substitute_authority):raise ValueError("invalid_burning_bulwark_successful_block_context")
 return {"schema_version":"burning-bulwark-successful-block-context-v1","session_id":session_id,"shield_owner":shield,"shield_action_id":shield_action_id,"shield_move_id":"burning-bulwark","blocked_attacker":attacker,"blocked_action_id":blocked_action_id,"blocked_move_id":blocked_move_id,"protection_authority":deepcopy(dict(protection_authority)),"action_blocked":action_blocked,"protection_bypass":protection_bypass,"substitute_authority":deepcopy(dict(substitute_authority)),"provenance":"explicit_existing_protection_block_context_v1"}
def build_burning_bulwark_reactive_burn_applicability_resolution(*,session_id:str,shield_owner:Mapping[str,Any],blocked_attacker:Mapping[str,Any],blocked_action_id:str,blocked_move_id:str,outcome:str,ability_authority:Mapping[str,Any],item_authority:Mapping[str,Any])->dict[str,Any]:
 shield,attacker=_owner(shield_owner),_owner(blocked_attacker)
 if not isinstance(session_id,str) or not session_id or shield["side"]==attacker["side"] or not all(isinstance(x,str) and x for x in (blocked_action_id,blocked_move_id)) or outcome not in {"applies","prevented"} or not _modifier(ability_authority) or not _modifier(item_authority):raise ValueError("invalid_burning_bulwark_reactive_burn_applicability_resolution")
 return {"schema_version":"burning-bulwark-reactive-burn-applicability-resolution-v1","session_id":session_id,"shield_owner":shield,"blocked_attacker":attacker,"blocked_action_id":blocked_action_id,"blocked_move_id":blocked_move_id,"outcome":outcome,"ability_authority":deepcopy(dict(ability_authority)),"item_authority":deepcopy(dict(item_authority)),"provenance":"explicit_canonical_burning_bulwark_burn_applicability_v1"}
def freeze_runtime_d0_burning_bulwark_reactive_burn_authority(*,strategy_d0:Mapping[str,Any],runtime_snapshot:Mapping[str,Any],shield_owner:Mapping[str,Any],shield_action_id:str,blocked_attacker:Mapping[str,Any],blocked_action:Mapping[str,Any],contact_authority:Mapping[str,Any]|None,protection_block_context:Mapping[str,Any]|None,applicability_resolution:Mapping[str,Any]|None)->dict[str,Any]:
 base=_base(strategy_d0,shield_owner,shield_action_id,blocked_attacker,blocked_action)
 if base is None:return _result("rejected","invalid_runtime_d0_or_burning_bulwark_burn_request",{})
 fresh=runtime_strategy_d0_freshness(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot)
 if fresh.get("status")!="current":return _result("rejected",fresh.get("reason","stale_runtime_d0"),base)
 context=_context(protection_block_context,base)
 if context is None:return _result("rejected","burning_bulwark_protection_block_context_binding_mismatch",base)
 if context["substitute_authority"].get("status")!="known_absent":return _result("incomplete","burning_bulwark_substitute_or_routing_authority_unresolved",base)
 if _contact(contact_authority,base)=="mismatch":return _result("rejected","burning_bulwark_contact_authority_binding_mismatch",base)
 if not isinstance(contact_authority,Mapping) or contact_authority.get("status")!="resolved":return _result("incomplete",contact_authority.get("reason","burning_bulwark_contact_authority_unavailable") if isinstance(contact_authority,Mapping) else "burning_bulwark_contact_authority_missing",base)
 if not context["action_blocked"] or context["protection_bypass"]:return _no(base,context,contact_authority,"protection_failed_or_bypassed")
 if contact_authority.get("contact_state")=="non_contact":return _no(base,context,contact_authority,"blocked_action_known_non_contact")
 if contact_authority.get("contact_state")!="contact":return _result("rejected","burning_bulwark_contact_state_invalid",base)
 condition=freeze_runtime_current_condition_authority(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot,owner=base["blocked_attacker"]); state=_condition(condition)
 if condition.get("status")=="rejected":return _result("rejected",condition.get("reason","burning_bulwark_current_condition_rejected"),base)
 if state is None:return _result("incomplete","burning_bulwark_blocked_attacker_condition_unknown",base)
 if state!="none":return _no(base,context,contact_authority,"blocked_attacker_already_statused",condition=condition)
 types=_types(runtime_snapshot,base["blocked_attacker"])
 if types.get("status")!="resolved":return _result(types["status"],types["reason"],base)
 if "fire" in types["types"]:return _no(base,context,contact_authority,"blocked_attacker_fire_type_immune",condition=condition,types=types)
 app=_app(applicability_resolution,base)
 if app=="mismatch":return _result("rejected","burning_bulwark_burn_applicability_binding_mismatch",base)
 if not isinstance(app,Mapping) or app["ability_authority"].get("status")=="unknown" or app["item_authority"].get("status")=="unknown":return _result("incomplete","burning_bulwark_relevant_prevention_authority_unknown",base)
 if _current_modifiers(runtime_snapshot,base["blocked_attacker"])!={"ability_authority":app["ability_authority"],"item_authority":app["item_authority"]}:return _result("rejected","burning_bulwark_relevant_prevention_authority_binding_mismatch",base)
 if app["outcome"]=="prevented":return _no(base,context,contact_authority,"reactive_burn_prevented",condition=condition,types=types,app=app)
 metadata=canonical_burning_bulwark_reactive_burn_metadata("burning-bulwark")
 if metadata is None:return _result("rejected","canonical_burning_bulwark_burn_metadata_invalid",base)
 return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"applies","rule_id":"burning_bulwark_blocked_contact_burn","condition_before":"none","condition_after":"burn","trigger":"burning_bulwark_successful_blocked_contact","probability":{"numerator":1,"denominator":1},"contact_authority":deepcopy(dict(contact_authority)),"protection_block_context":context,"condition_authority":condition,"type_authority":types,"applicability_resolution":app,"canonical_metadata":metadata,"provenance":"runtime_d0_canonical_burning_bulwark_blocked_contact_burn_v1"}
def materialize_detached_burning_bulwark_reactive_burn(*,authority:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(authority,Mapping) or authority.get("schema_version")!=SCHEMA_VERSION:return {"status":"rejected","reason":"invalid_burning_bulwark_reactive_burn_authority"}
 if authority.get("status")!="resolved":return {"status":authority.get("status","rejected"),"reason":authority.get("reason","burning_bulwark_burn_unavailable")}
 if authority.get("outcome")=="not_applicable":return {"status":"resolved","transition_applied":False,"owner":deepcopy(dict(authority["blocked_attacker"])),"source_authority":deepcopy(dict(authority)),"provenance":"detached_burning_bulwark_no_condition_transition_v1"}
 if authority.get("outcome")!="applies" or authority.get("condition_before")!="none" or authority.get("condition_after")!="burn" or authority.get("trigger")!="burning_bulwark_successful_blocked_contact" or authority.get("probability")!={"numerator":1,"denominator":1}:return {"status":"rejected","reason":"burning_bulwark_reactive_burn_result_invalid"}
 return {"status":"resolved","transition_applied":True,"owner":deepcopy(dict(authority["blocked_attacker"])),"hypothetical_condition_authority":{"status":"known_present","condition":"burn","condition_before":"known_none","condition_after":"burn","trigger":authority["trigger"],"source_consequence_id":authority["rule_id"],"provenance":"detached_burning_bulwark_blocked_contact_burn_transition_v1"},"source_authority":deepcopy(dict(authority)),"provenance":"detached_burning_bulwark_reactive_burn_overlay_v1"}
def _base(d0,shield,shield_action,attacker,action):
 try:s,a=_owner(shield),_owner(attacker)
 except ValueError:return None
 if not isinstance(d0,Mapping) or d0.get("status")!="resolved" or s["side"]==a["side"] or not isinstance(shield_action,str) or not shield_action or not isinstance(action,Mapping) or not isinstance(action.get("action_id"),str) or not isinstance(action.get("identity"),str):return None
 active=d0.get("active_owners",{})
 if active.get(s["side"])!=s or active.get(a["side"])!=a:return None
 return {"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(d0["decision_owner"]),"shield_owner":s,"shield_action_id":shield_action,"shield_move_id":"burning-bulwark","blocked_attacker":a,"blocked_action_id":action["action_id"],"blocked_move_id":action["identity"]}
def _context(value,base):
 if not isinstance(value,Mapping):return None
 try: expected=build_burning_bulwark_successful_block_context(session_id=base["session_id"],shield_owner=base["shield_owner"],shield_action_id=base["shield_action_id"],blocked_attacker=base["blocked_attacker"],blocked_action_id=base["blocked_action_id"],blocked_move_id=base["blocked_move_id"],protection_authority=value.get("protection_authority"),action_blocked=value.get("action_blocked"),protection_bypass=value.get("protection_bypass"),substitute_authority=value.get("substitute_authority"))
 except (TypeError,ValueError):return None
 return expected if value==expected else None
def _contact(value,base):
 if not isinstance(value,Mapping):return None
 keys={"session_id":base["session_id"],"source_runtime_fingerprint":base["source_runtime_fingerprint"],"source_branch_fingerprint":base["source_branch_fingerprint"],"decision_owner":base["decision_owner"],"action_id":base["blocked_action_id"],"move_id":base["blocked_move_id"],"attacker":base["blocked_attacker"],"target":base["shield_owner"]}
 return None if all(value.get(k)==v for k,v in keys.items()) else "mismatch"
def _app(value,base):
 if not isinstance(value,Mapping):return None
 try: expected=build_burning_bulwark_reactive_burn_applicability_resolution(session_id=base["session_id"],shield_owner=base["shield_owner"],blocked_attacker=base["blocked_attacker"],blocked_action_id=base["blocked_action_id"],blocked_move_id=base["blocked_move_id"],outcome=value.get("outcome"),ability_authority=value.get("ability_authority"),item_authority=value.get("item_authority"))
 except (TypeError,ValueError):return "mismatch"
 return expected if value==expected else "mismatch"
def _pokemon(snapshot,owner):
 state=snapshot.get("state",{}) if isinstance(snapshot,Mapping) else {}; row=state.get(f"{owner.get('side')}_side",{}).get("pokemon",{}).get(owner.get("slot_index")) if isinstance(state,Mapping) else None
 return row if isinstance(row,Mapping) and row.get("pokemon_id")==owner.get("pokemon_id") else None
def _types(snapshot,owner):
 row=_pokemon(snapshot,owner); types=row.get("current_type") if isinstance(row,Mapping) else None; provenance=row.get("current_type_provenance") if isinstance(row,Mapping) else None
 if row is None:return {"status":"rejected","reason":"burning_bulwark_blocked_attacker_runtime_identity_mismatch"}
 if not isinstance(types,list) or not types or any(not isinstance(v,str) or not v for v in types) or not isinstance(provenance,Mapping) or provenance.get("event_kind")!="current_type_observed" or provenance.get("trust")!="user_confirmed_observation":return {"status":"incomplete","reason":"burning_bulwark_blocked_attacker_type_unknown"}
 return {"status":"resolved","types":tuple(types),"provenance":"runtime_current_type_observed"}
def _condition(value):
 c=value.get("condition") if isinstance(value,Mapping) else None
 return "none" if isinstance(c,Mapping) and c.get("status")=="known_none" else c.get("condition") if isinstance(c,Mapping) and c.get("status")=="known_present" and c.get("condition") in _CONDS else None
def _current_modifiers(snapshot,owner):
 row=_pokemon(snapshot,owner)
 if not isinstance(row,Mapping):return None
 a,ap,i,ip=row.get("current_ability"),row.get("current_ability_provenance"),row.get("known_item"),row.get("known_item_provenance")
 if not isinstance(a,str) or not a or not _trusted(ap,"current_ability_observed") or not _trusted(ip,"current_item_observed"):return None
 item={"status":"known_absent"} if i is None and ip.get("status")=="known_absent" else {"status":"known","value":i} if isinstance(i,str) and i and ip.get("status")=="known" else None
 return {"ability_authority":{"status":"known","value":a},"item_authority":item} if item else None
def _no(base,context,contact,reason,**extra):return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"outcome":"not_applicable","condition_transition":None,"reason":reason,"contact_authority":deepcopy(dict(contact)),"protection_block_context":deepcopy(dict(context)),**{k:deepcopy(dict(v)) for k,v in extra.items() if v},"provenance":"runtime_d0_canonical_burning_bulwark_no_reactive_burn_v1"}
def _protection(value,shield):return isinstance(value,Mapping) and value.get("status")=="resolved" and value.get("owner")==shield and isinstance(value.get("metadata"),Mapping) and value["metadata"].get("move_id")=="burning-bulwark"
def _substitute(value):return isinstance(value,Mapping) and value.get("status") in {"known_absent","unknown"} and set(value).issuperset({"status"})
def _modifier(value):return isinstance(value,Mapping) and ((value.get("status")=="known" and set(value)=={"status","value"} and isinstance(value.get("value"),str) and bool(value["value"])) or (value.get("status") in {"known_absent","unknown"} and set(value)=={"status"}))
def _trusted(value,event):return isinstance(value,Mapping) and value.get("event_kind")==event and value.get("trust")=="user_confirmed_observation"
def _owner(value):
 if not isinstance(value,Mapping) or set(value)!=set(_OWNER) or not isinstance(value.get("session_id"),str) or not value["session_id"] or value.get("side") not in {"self","opponent"} or not isinstance(value.get("slot_index"),int) or isinstance(value["slot_index"],bool) or value["slot_index"]<0 or not isinstance(value.get("pokemon_id"),str) or not value["pokemon_id"]:raise ValueError("invalid_burning_bulwark_owner")
 return deepcopy(dict(value))
def _result(status,reason,base):return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
