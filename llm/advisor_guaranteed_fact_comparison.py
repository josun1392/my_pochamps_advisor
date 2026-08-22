"""Pure comparison over immediate-action facts guaranteed by exact or interval evidence."""
from copy import deepcopy
from typing import Any, Mapping, Sequence
from llm.advisor_transition_preview import fingerprint_transition_preview_state

HORIZON="immediate_action_consequence"; SCHEMA="deterministic-guaranteed-candidate-facts-v1"
def guaranteed_facts_from_exact_outcome(*,decision_owner:Mapping[str,Any],outcome:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(outcome,Mapping) or outcome.get("schema_version")!="deterministic-candidate-outcome-v1" or outcome.get("completeness")!="complete":return _r("incomplete","exact_outcome_incomplete")
 s=outcome.get("outcome_state");a=s.get("active") if isinstance(s,Mapping) else None; own=a.get(decision_owner.get("side")) if isinstance(a,Mapping) else None; other="opponent" if decision_owner.get("side")=="self" else "self";foe=a.get(other) if isinstance(a,Mapping) else None
 if not _active(own) or not _active(foe) or fingerprint_transition_preview_state(s)!=outcome.get("outcome_branch_fingerprint"):return _r("rejected","invalid_exact_outcome")
 return _facts(outcome["candidate_id"],outcome["action_type"],decision_owner,outcome["source_branch_fingerprint"],own["fainted"],foe["fainted"],own["current_hp"],"exact_outcome")
def guaranteed_facts_from_water_gun_interval(*,candidate:Mapping[str,Any],interval:Mapping[str,Any],own_current_hp:int)->dict[str,Any]:
 if not isinstance(interval,Mapping) or interval.get("schema_version")!="deterministic-predictive-damage-interval-v1" or interval.get("completeness")!="exact_complete":return _r("incomplete","interval_authority_incomplete")
 if not isinstance(candidate,Mapping) or candidate.get("candidate_id")!="attack:water-gun" or candidate.get("decision_owner")!=interval.get("decision_owner") or candidate.get("source_branch_fingerprint")!=interval.get("source_branch_fingerprint"):return _r("rejected","mismatched_interval_candidate")
 f=interval.get("guaranteed_facts",{}); own=interval["decision_owner"]
 return _facts(candidate["candidate_id"],candidate["action_type"],own,interval["source_branch_fingerprint"],False,True if f.get("guaranteed_target_KO") else False if f.get("guaranteed_target_survival") else None,own_current_hp,"water_gun_interval",possible_ko=bool(f.get("possible_target_KO")),substitute=deepcopy(f))
def compare_guaranteed_candidates(*,candidate_a:Mapping[str,Any],candidate_b:Mapping[str,Any])->dict[str,Any]:
 if not _valid(candidate_a) or not _valid(candidate_b):return _r("incomplete","insufficient_guaranteed_fact_authority")
 if any(candidate_a[k]!=candidate_b[k] for k in ("session_id","source_branch_fingerprint","decision_owner","horizon")):return _r("rejected","mismatched_guaranteed_fact_scope")
 for key,reason,prefer in (("guaranteed_own_fainted","avoids_self_ko",False),("guaranteed_opponent_fainted","causes_opponent_ko",True)):
  if candidate_a[key] is None or candidate_b[key] is None: continue
  if candidate_a[key]!=candidate_b[key]:return _pref("a" if candidate_a[key] is prefer else "b",reason,candidate_a,candidate_b)
 if candidate_a["exact_own_hp"] is not None and candidate_b["exact_own_hp"] is not None and candidate_a["guaranteed_own_fainted"] is False and candidate_b["guaranteed_own_fainted"] is False and candidate_a["exact_own_hp"]!=candidate_b["exact_own_hp"]:return _pref("a" if candidate_a["exact_own_hp"]>candidate_b["exact_own_hp"] else "b","safer_exact_self_hp",candidate_a,candidate_b)
 return {"status":"resolved","comparison":"tied_on_supported_facts","reason":"supported_guaranteed_facts_tie","facts":{"a":deepcopy(dict(candidate_a)),"b":deepcopy(dict(candidate_b))}}
def rank_guaranteed_candidates(*,candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
 ids=[x.get("candidate_id") if isinstance(x,Mapping) else None for x in candidates]
 if len(candidates)<2 or len(set(ids))!=len(ids):return _r("rejected","invalid_candidate_set")
 dominated=set();matrix=[];incomplete=False
 for i,a in enumerate(candidates):
  for b in candidates[i+1:]:
   r=compare_guaranteed_candidates(candidate_a=a,candidate_b=b);matrix.append(r)
   if r.get("status")!="resolved":incomplete=True
   elif r.get("comparison")=="preferred":dominated.add(b["candidate_id"] if r["preferred_candidate"]=="a" else a["candidate_id"])
 return {"status":"incomplete_comparison_set" if incomplete else "resolved","preferred_frontier":sorted(set(ids)-dominated),"pairwise_matrix":matrix}
def _facts(cid,kind,o,fp,own,foe,hp,evidence,possible_ko=False,substitute=None):return {"status":"resolved","schema_version":SCHEMA,"candidate_id":cid,"action_type":kind,"session_id":o["session_id"],"source_branch_fingerprint":fp,"decision_owner":deepcopy(dict(o)),"horizon":HORIZON,"evidence_class":evidence,"guaranteed_own_fainted":own,"guaranteed_opponent_fainted":foe,"exact_own_hp":hp,"possible_opponent_ko":possible_ko,"substitute_facts":substitute or {},"provenance":"current_predictive_guaranteed_facts_v1"}
def _valid(x):return isinstance(x,Mapping) and x.get("status")=="resolved" and x.get("schema_version")==SCHEMA and x.get("horizon")==HORIZON and isinstance(x.get("candidate_id"),str)
def _active(x):return isinstance(x,Mapping) and isinstance(x.get("current_hp"),int) and isinstance(x.get("max_hp"),int) and x["max_hp"]>0 and x.get("fainted") is (x["current_hp"]==0)
def _pref(w,r,a,b):return {"status":"resolved","comparison":"preferred","preferred_candidate":w,"reason":r,"facts":{"a":deepcopy(dict(a)),"b":deepcopy(dict(b))}}
def _r(s,r):return {"status":s,"reason":r}
