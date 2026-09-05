"""Exact Counter/Mirror Coat leaves from one detached incoming-event authority."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_recent_damage_retaliation_family import resolve_canonical_recent_damage_retaliation_move

SCHEMA_VERSION = "detached-recent-damage-retaliation-attack-leaf-v1"

def materialize_detached_recent_damage_retaliation_attack_leaves(*, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move: Mapping[str, Any], strict_hit_probability: Mapping[str, Any], incoming_event: Mapping[str, Any] | None, applicability: str) -> dict[str, Any]:
    canonical=resolve_canonical_recent_damage_retaliation_move(move=move)
    if canonical.get("status")!="resolved": return _result(canonical.get("status","rejected"),canonical.get("reason","catalog_unavailable"))
    active=strategy_d0.get("strategy_state",{}).get("active",{}); ah=active.get(attacker.get("side"),{}).get("current_hp"); th=active.get(target.get("side"),{}).get("current_hp")
    if not isinstance(ah,int) or not isinstance(th,int): return _result("incomplete","retaliation_execution_hp_unknown")
    if applicability not in {"applicable","immune","blocked"}: return _result("rejected","retaliation_applicability_invalid")
    pct=100 if strict_hit_probability.get("result")=="always_hit" else strict_hit_probability.get("probability_percent")
    if not isinstance(pct,int) or not 0<=pct<=100:return _result("rejected","retaliation_hit_probability_invalid")
    event_ok=isinstance(incoming_event,Mapping) and incoming_event.get("status")=="resolved" and incoming_event.get("recipient")==attacker and incoming_event.get("source_attacker")==target and incoming_event.get("source_category")==canonical["effect"]["qualifying_category"] and incoming_event.get("qualifying_event") is True and isinstance(incoming_event.get("hp_lost"),int) and incoming_event["hp_lost"]>=0
    leaves=[]
    for state,p in (("hit",pct),("miss",100-pct)):
      if not p: continue
      success=state=="hit" and applicability=="applicable" and event_ok
      damage=max(1,2*incoming_event["hp_lost"]) if success else 0
      outcome="success" if success else "miss" if state=="miss" else "immune" if applicability=="immune" else "blocked" if applicability=="blocked" else "failure_no_qualifying_recent_damage"
      post=max(0,th-damage); actual=th-post
      leaves.append({"leaf_id":f"{move['move_id']}:{outcome}","candidate_id":f"attack:{move['move_id']}","action_type":"attack","branch_path":((state,{"numerator":p,"denominator":100}),),"probability":{"numerator":p,"denominator":100},"hit_state":state,"critical_state":"not_applicable","damage_roll":"not_applicable","consequences":{"damage":damage,"own_final_hp":ah,"target_final_hp":post,"target_ko":post==0,"self_fainted":False,"secondary":None,"contact":"successful_contact_eligible" if success and canonical['effect']['contact'] else "not_applicable","source_hit_context":{"move_id":move['move_id'],"damage_route":"target","successful_damaging_hit":success},"recent_damage_retaliation":{"family":deepcopy(canonical['effect']),"outcome":outcome,"retaliation_target":deepcopy(dict(target)),"incoming_event":deepcopy(dict(incoming_event)) if isinstance(incoming_event,Mapping) else None,"raw_damage":damage,"actual_target_hp_loss":actual,"target_pre_hp":th,"target_post_hp":post,"derived_damage":damage}},"provenance":{"session_id":strategy_d0['session_id'],"source_runtime_fingerprint":strategy_d0['source_runtime_fingerprint'],"source_branch_fingerprint":strategy_d0['strategy_preview_fingerprint'],"decision_owner":deepcopy(dict(strategy_d0['decision_owner'])),"attacker":deepcopy(dict(attacker)),"target":deepcopy(dict(target)),"move_id":move['move_id'],"move_category":move['category'],"provenance":"strict_detached_recent_damage_retaliation_v1"}})
    return {"status":"evaluable","schema_version":SCHEMA_VERSION,"terminal_leaves":tuple(leaves),"terminal_probability_mass":{"numerator":1,"denominator":1},"component_manifest":{"accuracy":{"status":"resolved"},"critical":{"status":"not_applicable"},"damage_roll":{"status":"not_applicable"},"secondary":{"status":"not_applicable"}},"provenance":"strict_recent_damage_retaliation_to_terminal_leaves_v1"}

def _result(status: str, reason: str)->dict[str,Any]:return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
