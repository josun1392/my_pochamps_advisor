"""Strict current D0 reader for reducer-owned Disable state."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
SCHEMA_VERSION="runtime-d0-disable-restriction-authority-v1"
_OWNER={"session_id","side","slot_index","pokemon_id"}

def freeze_runtime_d0_disable_restriction_authority(*,strategy_d0:Mapping[str,Any],runtime_snapshot:Mapping[str,Any],owner:Mapping[str,Any])->dict[str,Any]:
    base=_base(strategy_d0,owner)
    if base is None:return _result("rejected","invalid_runtime_d0_or_disable_owner",{})
    fresh=runtime_strategy_d0_freshness(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot)
    if fresh.get("status")!="current":return _result("rejected",fresh.get("reason","stale_runtime_d0"),base)
    state=runtime_snapshot.get("state") if isinstance(runtime_snapshot,Mapping) else None; rows=state.get("current_disable_restrictions") if isinstance(state,Mapping) else None
    if not isinstance(rows,Mapping):return _result("incomplete","current_disable_restriction_authority_missing",base)
    row=rows.get(owner["side"])
    if not isinstance(row,Mapping):return _result("incomplete","current_disable_restriction_observation_missing",base)
    if not _row(row):return _result("rejected","disable_restriction_lifecycle_invalid",base)
    if row["owner"]!=dict(owner):
        if row["state"]!="not_active" or row["retired_reason"]!="switch_out":return _result("rejected","disable_restriction_owner_binding_mismatch",base)
        return _resolved(base,owner,row,row["owner"])
    return _resolved(base,owner,row)

def _resolved(base,owner,row,retired=None):
    out={"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"owner":deepcopy(dict(owner)),"state":row["state"],"disabled_move_id":row["disabled_move_id"],"remaining_target_turns":row["remaining_target_turns"],"activation_id":row["activation_id"],"source_action_id":row["source_action_id"],"last_used_execution_id":row["last_used_execution_id"],"retired_reason":row["retired_reason"],"reducer_lifecycle":{"application":deepcopy(dict(row["application_provenance"])),"current":deepcopy(dict(row["lifecycle_provenance"]))},"provenance":"strict_runtime_d0_current_disable_restriction_v1"}
    if retired is not None:out["retired_activation_owner"]=deepcopy(dict(retired))
    return out
def _row(r):
    req={"schema_version","owner","restriction","activation_id","source_action_id","source_move_id","disabled_move_id","last_used_execution_id","state","remaining_target_turns","applied_turn","last_completed_turn","retired_reason","application_provenance","lifecycle_provenance"}; active=r.get("state")=="active"; rem=r.get("remaining_target_turns")
    return set(r)==req and r.get("schema_version")=="reducer-action-restriction-lifecycle-v1" and r.get("restriction")==r.get("source_move_id")=="disable" and isinstance(r.get("owner"),Mapping) and set(r["owner"])==_OWNER and all(isinstance(r.get(k),str) and r[k] for k in ("activation_id","source_action_id","disabled_move_id","last_used_execution_id")) and r.get("state") in {"active","not_active"} and active==(isinstance(rem,int) and not isinstance(rem,bool) and 1<=rem<=4) and active==(r.get("retired_reason") is None) and all(isinstance(r.get(k),Mapping) and r[k].get("trust")=="user_confirmed_observation" for k in ("application_provenance","lifecycle_provenance"))
def _base(d0,owner):
    if not isinstance(d0,Mapping) or d0.get("status")!="resolved" or not isinstance(owner,Mapping) or set(owner)!=_OWNER or d0.get("active_owners",{}).get(owner.get("side"))!=dict(owner) or not all(isinstance(d0.get(k),str) and d0[k] for k in ("session_id","source_runtime_fingerprint","strategy_preview_fingerprint")):return None
    return {"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(dict(d0["decision_owner"])),"owner":deepcopy(dict(owner))}
def _result(status,reason,base):return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
