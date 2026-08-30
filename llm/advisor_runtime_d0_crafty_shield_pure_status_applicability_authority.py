"""Strict Crafty Shield applicability for one already-classified pure-status action."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_crafty_shield_protection import canonical_crafty_shield_protection_metadata
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
SCHEMA_VERSION="runtime-d0-crafty-shield-pure-status-applicability-authority-v1"
def freeze_runtime_d0_crafty_shield_pure_status_applicability_authority(*,strategy_d0:Mapping[str,Any],runtime_snapshot:Mapping[str,Any],guard_user:Mapping[str,Any],guard_action_id:str,incoming_execution_authority:Mapping[str,Any],protection_context:Mapping[str,Any]|None)->dict[str,Any]:
 base=_base(strategy_d0,guard_user,guard_action_id,incoming_execution_authority)
 if base is None:return _r("rejected","crafty_shield_binding_invalid",{})
 fresh=runtime_strategy_d0_freshness(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot)
 if fresh.get("status")!="current":return _r("rejected",fresh.get("reason","stale_runtime_d0"),base)
 if canonical_crafty_shield_protection_metadata("crafty-shield") is None:return _r("rejected","canonical_crafty_shield_metadata_invalid",base)
 if not isinstance(protection_context,Mapping):return _r("incomplete","crafty_shield_protection_context_missing",base)
 for k in ("session_id","guard_user","guard_action_id","incoming_actor","incoming_action_id","incoming_move_id","selected_target"):
  if protection_context.get(k)!=base.get(k):return _r("rejected","crafty_shield_protection_context_binding_mismatch",base)
 if not isinstance(protection_context.get("success"),bool) or not isinstance(protection_context.get("bypass"),bool):return _r("incomplete","crafty_shield_success_or_bypass_unknown",base)
 if not protection_context["success"] or protection_context["bypass"]:return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"not_applicable","reason":"shield_failed_or_bypassed","protection_context":deepcopy(dict(protection_context))}
 if base["selected_target"].get("side")!=base["guard_user"].get("side"):return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"not_applicable","reason":"target_outside_protected_side","protection_context":deepcopy(dict(protection_context))}
 return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"outcome":"prevented","protection_context":deepcopy(dict(protection_context)),"provenance":"strict_crafty_shield_pure_status_protection_v1"}
def _base(d:Any,g:Any,a:Any,x:Any)->dict[str,Any]|None:
 if not isinstance(d,Mapping) or d.get("status")!="resolved" or not isinstance(g,Mapping) or not isinstance(a,str) or not isinstance(x,Mapping) or x.get("status")!="resolved":return None
 if d.get("active_owners",{}).get(g.get("side"))!=dict(g) or x.get("actor",{}).get("side")==g.get("side"):return None
 target=x.get("target");actor=x.get("actor")
 if not isinstance(target,Mapping) or not isinstance(actor,Mapping):return None
 return {"session_id":d["session_id"],"source_runtime_fingerprint":d["source_runtime_fingerprint"],"source_branch_fingerprint":d["strategy_preview_fingerprint"],"decision_owner":deepcopy(d["decision_owner"]),"guard_user":deepcopy(dict(g)),"guard_action_id":a,"guard_move_id":"crafty-shield","incoming_actor":deepcopy(dict(actor)),"incoming_action_id":x.get("action_id"),"incoming_move_id":x.get("move_id"),"selected_target":deepcopy(dict(target))}
def _r(s:str,r:str,b:Mapping[str,Any])->dict[str,Any]:return {"status":s,"schema_version":SCHEMA_VERSION,**deepcopy(dict(b)),"reason":r}
