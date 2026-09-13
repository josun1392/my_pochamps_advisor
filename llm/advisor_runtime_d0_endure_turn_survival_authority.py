"""Canonical, turn-local Endure execution and survival authority."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_runtime_d0_nonconsecutive_protection_success_authority import freeze_runtime_d0_nonconsecutive_protection_success_authority
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
SCHEMA_VERSION = "runtime-d0-endure-turn-survival-authority-v1"
def canonical_endure_metadata(move_id: Any) -> dict[str, Any] | None:
    if move_id != "endure": return None
    return {"move_id":"endure","category":"status","target":"user","protection_kind":"turn_local_survival","blocks_supported_direct_damage":False,"survives_lethal_damage_at_one_hp":True}
def freeze_runtime_d0_endure_turn_survival_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], endure_user: Mapping[str, Any], endure_action: Mapping[str, Any]) -> dict[str, Any]:
    base=_base(strategy_d0,endure_user,endure_action)
    if base is None:return _result("rejected","invalid_endure_turn_survival_request",{})
    fresh=runtime_strategy_d0_freshness(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot)
    if fresh.get("status")!="current":return _result("rejected",fresh.get("reason","stale_runtime_d0"),base)
    success=freeze_runtime_d0_nonconsecutive_protection_success_authority(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot,protection_owner=endure_user,protection_action=endure_action)
    if success.get("status")!="resolved":return _result(_status(success),success.get("reason","endure_success_history_unavailable"),base,protection_success_authority=success)
    inner=success.get("protection_success_authority")
    if not isinstance(inner,Mapping) or inner.get("owner")!=dict(endure_user) or inner.get("previous_successful_protection_count")!=0:return _result("rejected","endure_success_authority_binding_mismatch",base,protection_success_authority=success)
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"canonical_metadata":canonical_endure_metadata("endure"),"protection_success_authority":deepcopy(dict(inner)),"turn_local_activation_id":f"{endure_action['action_id']}:endure-turn-local","provenance":"runtime_d0_current_nonconsecutive_endure_turn_survival_v1"}
def materialize_detached_endure_turn_context(*, authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(authority,Mapping) or authority.get("schema_version")!=SCHEMA_VERSION:return {"status":"rejected","reason":"endure_turn_survival_authority_invalid"}
    if authority.get("status")!="resolved":return {"status":_status(authority),"reason":authority.get("reason","endure_turn_survival_unavailable")}
    required=("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","endure_user","endure_action_id","endure_move_id","turn_local_activation_id","protection_success_authority")
    if any(key not in authority for key in required) or authority.get("endure_move_id")!="endure" or canonical_endure_metadata(authority.get("endure_move_id")) is None:return {"status":"rejected","reason":"endure_turn_survival_authority_shape_invalid"}
    success=authority["protection_success_authority"]
    if not isinstance(success,Mapping) or success.get("schema_version")!="branch-protection-success-v1" or success.get("owner")!=authority["endure_user"] or success.get("previous_successful_protection_count")!=0:return {"status":"rejected","reason":"endure_turn_survival_success_binding_invalid"}
    return {"status":"resolved","schema_version":"detached-endure-turn-context-v1",**{key:deepcopy(authority[key]) for key in required},"endure_move_id":"endure","active_for":"current_immediate_turn_only","provenance":"validated_runtime_d0_endure_turn_survival_authority_v1"}
def apply_endure_turn_survival_to_hit(*, context: Mapping[str, Any] | None, target: Mapping[str, Any], hp_before: int, raw_damage: int, actual_damage: int, source_hit: Mapping[str, Any]) -> dict[str, Any]:
    if context is None:return {"actual_damage":actual_damage,"post_hp":max(0,hp_before-actual_damage),"survival":{"outcome":"not_applicable"}}
    if not isinstance(context,Mapping) or context.get("schema_version")!="detached-endure-turn-context-v1" or context.get("status")!="resolved":return {"status":"rejected","reason":"endure_turn_context_invalid"}
    if context.get("endure_user")!=dict(target):return {"status":"rejected","reason":"endure_turn_context_target_binding_mismatch"}
    if not all(isinstance(value,int) and not isinstance(value,bool) and value>=0 for value in (hp_before,raw_damage,actual_damage)) or actual_damage>hp_before:return {"status":"rejected","reason":"endure_turn_survival_hp_transition_invalid"}
    if hp_before<=0 or raw_damage<hp_before:return {"actual_damage":actual_damage,"post_hp":max(0,hp_before-actual_damage),"survival":{"outcome":"not_triggered","reason":"nonlethal_damage"}}
    applied=hp_before-1
    return {"actual_damage":applied,"post_hp":1,"survival":{"outcome":"applied","target_final_hp":1,"hp_before":hp_before,"raw_damage":raw_damage,"actual_damage":applied,"turn_local_activation_id":context["turn_local_activation_id"],"endure_user":deepcopy(dict(target)),"source_hit":deepcopy(dict(source_hit)),"provenance":"exact_detached_endure_turn_survival_clamp_v1"}}
def _base(d0: Any,user: Any,action: Any)->dict[str,Any]|None:
    if not isinstance(d0,Mapping) or d0.get("status")!="resolved" or not isinstance(user,Mapping) or d0.get("active_owners",{}).get(user.get("side"))!=dict(user) or not isinstance(action,Mapping):return None
    metadata=action.get("metadata_authority",{}).get("metadata") if isinstance(action.get("metadata_authority"),Mapping) else action.get("move_metadata_authority",{}).get("metadata") if isinstance(action.get("move_metadata_authority"),Mapping) else None
    if not isinstance(metadata,Mapping) or canonical_endure_metadata(metadata.get("move_id")) is None or metadata.get("category")!="status" or metadata.get("target")!="user" or metadata.get("accuracy") is not None or action.get("action_type")!="attack" or not isinstance(action.get("action_id"),str):return None
    if any(not isinstance(d0.get(key),str) or not d0[key] for key in ("session_id","source_runtime_fingerprint","strategy_preview_fingerprint")):return None
    return {"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(dict(d0["decision_owner"])),"endure_user":deepcopy(dict(user)),"endure_action_id":action["action_id"],"endure_move_id":"endure"}
def _status(value: Any)->str:return value.get("status") if isinstance(value,Mapping) and value.get("status") in {"incomplete","unsupported","rejected"} else "rejected"
def _result(status:str,reason:str,base:Mapping[str,Any],**extra:Any)->dict[str,Any]:return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason,**deepcopy(extra)}
