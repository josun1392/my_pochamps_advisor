"""Exact Endeavor leaves from the shared special-damage execution envelope."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_detached_endeavor_hp_difference_damage import materialize_detached_endeavor_hp_difference_damage

SCHEMA_VERSION = "detached-endeavor-hp-difference-damage-attack-leaf-v1"


def materialize_detached_endeavor_hp_difference_damage_attack_leaves(*, strategy_d0: Mapping[str, Any], execution_authority: Mapping[str, Any], strict_hit_probability: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, execution_authority)
    if base is None: return _result("rejected", "endeavor_execution_authority_invalid", {})
    hit = _hit(strict_hit_probability, base)
    if isinstance(hit, str): return _result("rejected", hit, base)
    attacker_hp, target_hp = execution_authority.get("execution_attacker_hp"), execution_authority.get("execution_target_hp")
    active = strategy_d0.get("strategy_state", {}).get("active", {})
    if attacker_hp != active.get(base["attacker"]["side"], {}).get("current_hp") or target_hp != active.get(base["target"]["side"], {}).get("current_hp"): return _result("rejected", "endeavor_execution_hp_binding_mismatch", base)
    arithmetic = materialize_detached_endeavor_hp_difference_damage(move=execution_authority["canonical_move_metadata"], attacker_hp={"current_hp": attacker_hp, "max_hp": execution_authority["attacker_hp_authority"]["max_hp"], "fainted": False}, target_hp={"current_hp": target_hp, "max_hp": execution_authority["target_hp_authority"]["max_hp"], "fainted": False}, hit_state="hit", applicability=execution_authority["applicability"])
    if arithmetic.get("status") != "resolved": return _result(arithmetic.get("status", "rejected"), arithmetic.get("reason", "endeavor_arithmetic_unavailable"), base)
    leaves=[]
    for state, percent in (("hit", hit), ("miss", 100-hit)):
        if percent == 0: continue
        row = arithmetic if state == "hit" else materialize_detached_endeavor_hp_difference_damage(move=execution_authority["canonical_move_metadata"], attacker_hp={"current_hp": attacker_hp, "max_hp": execution_authority["attacker_hp_authority"]["max_hp"], "fainted": False}, target_hp={"current_hp": target_hp, "max_hp": execution_authority["target_hp_authority"]["max_hp"], "fainted": False}, hit_state="miss", applicability=execution_authority["applicability"])
        success = row["outcome"] == "success"
        leaves.append({"leaf_id":f"endeavor:{row['outcome']}","candidate_id":"attack:endeavor","action_type":"attack","branch_path":((state,{"numerator":percent,"denominator":100}),),"probability":{"numerator":percent,"denominator":100},"hit_state":state,"critical_state":"not_applicable","damage_roll":"not_applicable","consequences":{"damage":row["damage"],"own_final_hp":attacker_hp,"target_final_hp":row["target_post_hp"],"target_ko":False,"self_fainted":False,"secondary":None,"contact":"successful_contact_eligible" if success else "not_applicable","source_hit_context":{"move_id":"endeavor","damage_route":"target","successful_damaging_hit":success},"endeavor_hp_difference_damage":{**deepcopy(row),"target_route":"target"}},"provenance":{**base,"execution_authority":deepcopy(dict(execution_authority)),"provenance":"strict_d0_endeavor_special_damage_execution_envelope_v1"}})
    return {"status":"evaluable","schema_version":SCHEMA_VERSION,"terminal_leaves":tuple(leaves),"terminal_probability_mass":{"numerator":1,"denominator":1},"component_manifest":{"accuracy":{"status":"resolved"},"critical":{"status":"not_applicable"},"damage_roll":{"status":"not_applicable"},"secondary":{"status":"not_applicable"}},**base,"provenance":"strict_endeavor_special_damage_execution_to_terminal_leaves_v1"}


def _base(d0: Any, authority: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or not isinstance(authority, Mapping) or authority.get("status")!="resolved" or authority.get("schema_version")!="runtime-d0-special-damage-execution-authority-v1" or authority.get("special_damage_family")!="hp_difference_damage" or authority.get("move_id")!="endeavor": return None
    keys=("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","attacker","target","move_id")
    if any(authority.get(k)!=d0.get({"source_branch_fingerprint":"strategy_preview_fingerprint"}.get(k,k)) for k in ("session_id","source_runtime_fingerprint","decision_owner")) or authority.get("source_branch_fingerprint")!=d0.get("strategy_preview_fingerprint") or authority.get("attacker")!=d0.get("decision_owner"): return None
    return {key:deepcopy(authority[key]) for key in keys}


def _hit(value: Any, base: Mapping[str, Any]) -> int | str:
    if not isinstance(value,Mapping) or value.get("status")!="resolved" or value.get("schema_version")!="strict-deterministic-hit-probability-v1" or any(value.get(k)!=base.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","attacker","target","move_id")): return "endeavor_strict_hit_probability_binding_mismatch"
    p=100 if value.get("result")=="always_hit" else value.get("probability_percent")
    return p if isinstance(p,int) and not isinstance(p,bool) and 0<=p<=100 else "endeavor_strict_hit_probability_invalid"


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
