"""Supplied-authority-only bridge from one D0 to comparison outcomes."""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping,Sequence
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_observed_damage_application import apply_exact_observed_damage
from llm.advisor_incoming_active_materialization import materialize_incoming_active_branch

def materialize_candidates(*,decision_state:Mapping[str,Any],decision_owner:Mapping[str,Any],candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
 fp=fingerprint_transition_preview_state(decision_state)
 if not isinstance(fp,str) or not isinstance(candidates,Sequence):return _r("rejected","invalid_decision_root")
 out=[]
 for c in candidates: out.append(_one(decision_state,fp,decision_owner,c))
 return {"status":"resolved","decision_branch_fingerprint":fp,"outcomes":out}
def _one(state,fp,owner,c):
 if not isinstance(c,Mapping) or c.get("schema_version")!="deterministic-action-candidate-v1" or c.get("decision_owner")!=dict(owner) or c.get("source_branch_fingerprint")!=fp or not isinstance(c.get("candidate_id"),str):return _r("rejected","stale_or_invalid_candidate_authority")
 kind,payload=c.get("action_type"),c.get("action_authority")
 if kind=="attack":
  if not isinstance(payload,Mapping):return _incomplete(c,"observation_required")
  result=apply_exact_observed_damage(branch_state=state,source_branch_fingerprint=fp,user=payload.get("user"),target_owner=payload.get("target_owner"),damage_amount=payload.get("damage_amount"))
 elif kind=="manual_switch": result=materialize_incoming_active_branch(source_branch=state,source_branch_fingerprint=fp,incoming_authority=payload) if isinstance(payload,Mapping) else _incomplete(c,"switch_authority_required")
 else:return _incomplete(c,"unsupported_execution_family")
 if result.get("status")!="resolved":return _incomplete(c,result.get("reason","execution_incomplete"))
 return {"status":"complete","outcome":{"schema_version":"deterministic-candidate-outcome-v1","candidate_id":c["candidate_id"],"action_type":kind,"source_branch_fingerprint":fp,"outcome_state":result["next_state"],"outcome_branch_fingerprint":result["resulting_branch_fingerprint"],"completeness":"complete"}}
def _incomplete(c,reason):return {"status":"incomplete","candidate_id":c.get("candidate_id") if isinstance(c,Mapping) else None,"reason":reason}
def _r(status,reason):return {"status":status,"reason":reason}
