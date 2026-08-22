"""Giga Drain-only trusted observed damage plus final drain consequence."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_observed_damage_application import apply_exact_observed_damage, apply_exact_observed_drain_consequence, exact_owner
from llm.advisor_transition_preview import fingerprint_transition_preview_state

SCHEMA_VERSION="observed-damage-plus-drain-result-v1"; _PROVENANCE="trusted_observed_damage_plus_drain_result_v1"
_KEYS=frozenset({"schema_version","session_id","source_branch_fingerprint","user","target_owner","move_id","damage_amount","damaging_hit_result","drain_result","drain_consequence","drain_amount","provenance"})
def materialize_observed_giga_drain(*,branch_state:Mapping[str,Any],source_branch_fingerprint:str,observed_result:Mapping[str,Any])->dict[str,Any]:
    if fingerprint_transition_preview_state(branch_state)!=source_branch_fingerprint:return _r("rejected","stale_or_invalid_observed_giga_drain_branch")
    if not _valid(observed_result,source_branch_fingerprint):return _r("rejected","invalid_observed_giga_drain_result")
    user,target=observed_result["user"],observed_result["target_owner"]
    damage=apply_exact_observed_damage(branch_state=branch_state,source_branch_fingerprint=source_branch_fingerprint,user=user,target_owner=target,damage_amount=observed_result["damage_amount"])
    if damage.get("status")!="resolved":return damage
    f1,fp=damage["next_state"],damage["resulting_branch_fingerprint"]
    if observed_result["drain_result"]=="not_applied":return {**damage,"f1_branch_fingerprint":fp,"observed_damage_plus_drain_result":deepcopy(dict(observed_result)),"drain":"not_applied"}
    authority={"schema_version":"observed-giga-drain-consequence-authority-v1","source_branch_fingerprint":fp,"owner":deepcopy(dict(user)),"consequence":observed_result["drain_consequence"],"amount":observed_result["drain_amount"],"provenance":_PROVENANCE}
    consequence=apply_exact_observed_drain_consequence(branch_state=f1,source_branch_fingerprint=fp,drain_authority=authority)
    if consequence.get("status")!="resolved":return consequence
    return {"status":"resolved","source_branch_fingerprint":source_branch_fingerprint,"f1_branch_fingerprint":fp,"resulting_branch_fingerprint":consequence["resulting_branch_fingerprint"],"next_state":consequence["next_state"],"observed_damage_plus_drain_result":deepcopy(dict(observed_result)),"drain_authority":authority,"damage_application":damage["damage_application"],"drain_application":consequence["drain_application"],"materialization":"pure_idempotent"}
def _valid(v:Any,fp:str)->bool:
    if not isinstance(v,Mapping) or set(v)!=_KEYS:return False
    u,t,a,d=v.get("user"),v.get("target_owner"),v.get("drain_amount"),v.get("damage_amount"); result=v.get("drain_result"); kind=v.get("drain_consequence")
    consequence_ok=(result=="applied" and kind in {"heal","self_damage"} and isinstance(a,int) and not isinstance(a,bool) and a>0) or (result=="not_applied" and kind is None and a is None)
    return exact_owner(u) and exact_owner(t) and v.get("schema_version")==SCHEMA_VERSION and v.get("provenance")==_PROVENANCE and v.get("move_id")=="giga-drain" and v.get("damaging_hit_result")=="applied" and isinstance(d,int) and not isinstance(d,bool) and d>0 and consequence_ok and v.get("source_branch_fingerprint")==fp and v.get("session_id")==u["session_id"]==t["session_id"] and u["side"]!=t["side"]
def _r(status:str,reason:str)->dict[str,Any]:return {"status":status,"reason":reason}
