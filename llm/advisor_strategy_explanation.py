"""Presentation-only view of detached strategy orchestration evidence."""
from copy import deepcopy
from typing import Any,Mapping
SCHEMA="deterministic-strategy-explanation-v1"
def explain_detached_strategy(*,orchestration:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(orchestration,Mapping) or orchestration.get("schema_version")!="deterministic-strategy-orchestration-result-v1":return _r("rejected","invalid_orchestration_result")
 owner=orchestration.get("decision_owner");candidates=orchestration.get("candidates");ranking=orchestration.get("ranking")
 if not isinstance(owner,Mapping) or orchestration.get("session_id")!=owner.get("session_id") or not isinstance(orchestration.get("decision_branch_fingerprint"),str) or not isinstance(candidates,list) or not isinstance(ranking,Mapping):return _r("rejected","inconsistent_orchestration_d0")
 frontier=ranking.get("preferred_frontier",[])
 if not isinstance(frontier,list) or any(not isinstance(x,str) for x in frontier):return _r("rejected","invalid_orchestration_ranking")
 reasons=_reasons(ranking);rows=[]
 for row in candidates:
  if not isinstance(row,Mapping) or not isinstance(row.get("candidate_id"),str):return _r("rejected","invalid_candidate_evidence")
  facts=row.get("facts") if isinstance(row.get("facts"),Mapping) else {}
  rows.append({"candidate_id":row["candidate_id"],"action_type":row.get("action_type"),"evidence_class":row.get("evidence_class"),"execution_readiness":row.get("execution_readiness"),"preferred_frontier_member":row["candidate_id"] in frontier,"comparison_reasons":reasons.get(row["candidate_id"],[]),"guaranteed_facts":deepcopy(dict(facts)) if facts else None,"interval":deepcopy(row.get("interval")) if isinstance(row.get("interval"),Mapping) else None,"incomplete_reason":row.get("reason") if row.get("evidence_class")=="incomplete" else None,"provenance":row.get("provenance")})
 status="selection_incomplete" if orchestration.get("selection_completeness")!="complete" else ranking.get("status")
 return {"status":"resolved","schema_version":SCHEMA,"session_id":orchestration["session_id"],"decision_branch_fingerprint":orchestration["decision_branch_fingerprint"],"decision_owner":deepcopy(dict(owner)),"horizon":"immediate_action_consequence","overall_status":status,"preferred_frontier":sorted(frontier),"candidates":sorted(rows,key=lambda x:x["candidate_id"]),"comparison_matrix":deepcopy(ranking.get("pairwise_matrix",[])),"provenance":"detached_strategy_explanation_v1"}
def _reasons(r):
 out={}
 for x in r.get("pairwise_matrix",[]) if isinstance(r.get("pairwise_matrix"),list) else []:
  if isinstance(x,Mapping) and x.get("comparison")=="preferred" and isinstance(x.get("preferred_candidate"),str):out.setdefault(x["preferred_candidate"],[]).append(x.get("reason"))
 return out
def _r(s,r):return {"status":s,"reason":r}
