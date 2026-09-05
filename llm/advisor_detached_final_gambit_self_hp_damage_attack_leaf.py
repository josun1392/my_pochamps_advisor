from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping
from llm.advisor_detached_final_gambit_self_hp_damage import materialize_detached_final_gambit_self_hp_damage
SCHEMA_VERSION="detached-final-gambit-self-hp-damage-attack-leaf-v1"
def materialize_detached_final_gambit_self_hp_damage_attack_leaves(*,strategy_d0:Mapping[str,Any],execution_authority:Mapping[str,Any],strict_hit_probability:Mapping[str,Any])->dict[str,Any]:
 b=_base(strategy_d0,execution_authority)
 if b is None:return _result("rejected","final_gambit_execution_authority_invalid",{})
 h=_hit(strict_hit_probability,b)
 if isinstance(h,str):return _result("rejected",h,b)
 a,t=execution_authority.get("execution_attacker_hp"),execution_authority.get("execution_target_hp"); active=strategy_d0.get("strategy_state",{}).get("active",{})
 if a!=active.get(b["attacker"]["side"],{}).get("current_hp") or t!=active.get(b["target"]["side"],{}).get("current_hp"):return _result("rejected","final_gambit_execution_hp_binding_mismatch",b)
 rows=[]
 for state,p in (("hit",h),("miss",100-h)):
  if not p:continue
  r=materialize_detached_final_gambit_self_hp_damage(move=execution_authority["canonical_move_metadata"],attacker_hp={"current_hp":a,"max_hp":execution_authority["attacker_hp_authority"]["max_hp"],"fainted":False},target_hp={"current_hp":t,"max_hp":execution_authority["target_hp_authority"]["max_hp"],"fainted":False},hit_state=state,applicability=execution_authority["applicability"])
  if r.get("status")!="resolved":return _result(r.get("status","rejected"),r.get("reason","final_gambit_arithmetic_unavailable"),b)
  success=r["outcome"]=="success"
  rows.append({"leaf_id":f"final_gambit:{r['outcome']}","candidate_id":"attack:final-gambit","action_type":"attack","branch_path":((state,{"numerator":p,"denominator":100}),),"probability":{"numerator":p,"denominator":100},"hit_state":state,"critical_state":"not_applicable","damage_roll":"not_applicable","consequences":{"damage":r["raw_damage"],"own_final_hp":r["attacker_post_hp"],"target_final_hp":r["target_post_hp"],"target_ko":r["target_fainted"],"self_fainted":r["attacker_fainted"],"secondary":None,"contact":"successful_contact_eligible" if success else "not_applicable","source_hit_context":{"move_id":"final-gambit","damage_route":"target","successful_damaging_hit":success},"final_gambit_self_hp_damage":{**deepcopy(r),"target_route":"target"}},"provenance":{**b,"execution_authority":deepcopy(dict(execution_authority)),"provenance":"strict_d0_final_gambit_special_damage_execution_envelope_v1"}})
 return {"status":"evaluable","schema_version":SCHEMA_VERSION,"terminal_leaves":tuple(rows),"terminal_probability_mass":{"numerator":1,"denominator":1},"component_manifest":{"accuracy":{"status":"resolved"},"critical":{"status":"not_applicable"},"damage_roll":{"status":"not_applicable"},"secondary":{"status":"not_applicable"}},**b}
def _base(d:Any,a:Any)->dict[str,Any]|None:
 if not isinstance(d,Mapping) or not isinstance(a,Mapping) or a.get("status")!="resolved" or a.get("special_damage_family")!="self_current_hp_damage" or a.get("move_id")!="final-gambit":return None
 if a.get("attacker")!=d.get("decision_owner") or any(a.get(k)!=d.get({"source_branch_fingerprint":"strategy_preview_fingerprint"}.get(k,k)) for k in ("session_id","source_runtime_fingerprint","decision_owner")) or a.get("source_branch_fingerprint")!=d.get("strategy_preview_fingerprint"):return None
 return {k:deepcopy(a[k]) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","attacker","target","move_id")}
def _hit(v:Any,b:Mapping[str,Any])->int|str:
 if not isinstance(v,Mapping) or v.get("status")!="resolved" or any(v.get(k)!=b.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","attacker","target","move_id")):return "final_gambit_hit_binding_mismatch"
 p=100 if v.get("result")=="always_hit" else v.get("probability_percent");return p if isinstance(p,int) and not isinstance(p,bool) and 0<=p<=100 else "final_gambit_hit_invalid"
def _result(s:str,r:str,b:Mapping[str,Any])->dict[str,Any]:return {"status":s,"schema_version":SCHEMA_VERSION,**deepcopy(dict(b)),"reason":r}
