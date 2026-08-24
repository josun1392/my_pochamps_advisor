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
  uncertainty=_hit_miss_uncertainty(row)
  critical=_critical_hit_uncertainty(uncertainty,row.get("candidate_id")) if uncertainty is not None else None
  if row.get("evidence_class")=="hit_miss_uncertainty" and uncertainty is None:return _r("rejected","invalid_hit_miss_uncertainty_evidence")
  if critical is _INVALID:return _r("rejected","invalid_critical_hit_uncertainty_evidence")
  rolls=_roll_summaries(uncertainty)
  rows.append({"candidate_id":row["candidate_id"],"action_type":row.get("action_type"),"evidence_class":row.get("evidence_class"),"execution_readiness":row.get("execution_readiness"),"preferred_frontier_member":row["candidate_id"] in frontier,"comparison_reasons":reasons.get(row["candidate_id"],[]),"guaranteed_facts":deepcopy(dict(facts)) if facts else None,"interval":deepcopy(row.get("interval")) if isinstance(row.get("interval"),Mapping) else None,"hit_miss_uncertainty":uncertainty,"critical_hit_uncertainty":critical,"damage_roll_summaries":rolls,"incomplete_reason":row.get("reason") if row.get("evidence_class")=="incomplete" else None,"provenance":row.get("provenance")})
 status="selection_incomplete" if orchestration.get("selection_completeness")!="complete" else ranking.get("status")
 return {"status":"resolved","schema_version":SCHEMA,"session_id":orchestration["session_id"],"decision_branch_fingerprint":orchestration["decision_branch_fingerprint"],"decision_owner":deepcopy(dict(owner)),"horizon":"immediate_action_consequence","overall_status":status,"preferred_frontier":sorted(frontier),"candidates":sorted(rows,key=lambda x:x["candidate_id"]),"comparison_matrix":deepcopy(ranking.get("pairwise_matrix",[])),"provenance":"detached_strategy_explanation_v1"}
def _reasons(r):
 out={}
 for x in r.get("pairwise_matrix",[]) if isinstance(r.get("pairwise_matrix"),list) else []:
  if isinstance(x,Mapping) and x.get("comparison")=="preferred" and isinstance(x.get("preferred_candidate"),str):out.setdefault(x["preferred_candidate"],[]).append(x.get("reason"))
 return out
def _hit_miss_uncertainty(row):
 value=row.get("uncertainty") if isinstance(row,Mapping) else None
 if not isinstance(value,Mapping):return None
 if value.get("status")!="resolved" or value.get("schema_version")!="deterministic-predictive-hit-miss-uncertainty-v1" or value.get("candidate_id",f"attack:{value.get('move_id')}")!=row.get("candidate_id"):return None
 if not isinstance(value.get("probability_percent"),int) or not 0<=value["probability_percent"]<=100 or not isinstance(value.get("branches"),(tuple,list)) or not isinstance(value.get("guaranteed_facts"),Mapping):return None
 return deepcopy(dict(value))
_INVALID=object()
def _critical_hit_uncertainty(hit_miss,candidate_id):
 if not isinstance(hit_miss,Mapping):return None
 branches=hit_miss.get("branches")
 hit=next((x for x in branches if isinstance(x,Mapping) and x.get("branch")=="hit"),None) if isinstance(branches,(tuple,list)) else None
 value=hit.get("consequences",{}).get("critical_hit_uncertainty") if isinstance(hit,Mapping) and isinstance(hit.get("consequences"),Mapping) else None
 if value is None:return None
 if not isinstance(value,Mapping) or value.get("status")!="resolved" or value.get("schema_version")!="deterministic-predictive-critical-hit-uncertainty-v1" or value.get("move_id")!=candidate_id.removeprefix("attack:"):return _INVALID
 probability=value.get("critical_probability"); leaves=value.get("branches")
 if not isinstance(probability,Mapping) or not all(isinstance(probability.get(k),int) and not isinstance(probability.get(k),bool) for k in ("numerator","denominator")) or probability["denominator"]<=0 or not 0<=probability["numerator"]<=probability["denominator"] or not isinstance(leaves,(tuple,list)) or not all(isinstance(x,Mapping) and x.get("branch") in {"non_critical","critical"} for x in leaves):return _INVALID
 return deepcopy(dict(value))
def _roll_summaries(hit_miss):
 if not isinstance(hit_miss,Mapping):return ()
 branches=hit_miss.get("branches");hit=next((x for x in branches if isinstance(x,Mapping) and x.get("branch")=="hit"),None) if isinstance(branches,(tuple,list)) else None
 if not isinstance(hit,Mapping):return ()
 consequences=hit.get("consequences") if isinstance(hit.get("consequences"),Mapping) else {}
 critical=consequences.get("critical_hit_uncertainty") if isinstance(consequences,Mapping) else None
 leaves=[("hit",consequences)] if not isinstance(critical,Mapping) else [(f"hit/{x.get('branch')}",x.get("consequences")) for x in critical.get("branches",()) if isinstance(x,Mapping)]
 result=[]
 for path,leaf in leaves:
  ledger=leaf.get("damage_roll_uncertainty") if isinstance(leaf,Mapping) else None; interval=leaf.get("interval") if isinstance(leaf,Mapping) else None
  outcomes=ledger.get("outcomes") if isinstance(ledger,Mapping) else None; hp=interval.get("target_hp_before") if isinstance(interval,Mapping) else None
  if not isinstance(outcomes,(tuple,list)) or len(outcomes)!=16 or not isinstance(hp,int):continue
  damage=[x.get("damage") for x in outcomes if isinstance(x,Mapping) and isinstance(x.get("damage"),int)]
  if len(damage)!=16:continue
  ko=sum(value>=hp for value in damage)
  result.append({"branch_path":path,"critical_scope":ledger.get("critical_scope"),"exact_roll_count":16,"min_damage":min(damage),"max_damage":max(damage),"ko_roll_count":ko,"conditional_ko_probability":{"numerator":ko,"denominator":16},"damage_value_multiplicity":deepcopy(ledger.get("damage_value_multiplicity",()))})
 return tuple(result)
def _r(s,r):return {"status":s,"reason":r}
