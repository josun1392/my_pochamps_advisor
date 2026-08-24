"""Pure coordinator for the bounded detached strategy components."""
from typing import Any, Mapping
from llm.advisor_current_state_candidate_discovery import discover_candidates
from llm.advisor_current_execution_authority import enrich_discovered_candidates
from llm.advisor_candidate_outcome_materialization import materialize_candidates
from llm.advisor_predictive_fixed_damage_outcome import enrich_predictive_attack_candidate, materialize_predictive_fixed_damage_outcome
from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval
from llm.advisor_predictive_water_gun_interval import build_predictive_water_gun_interval
from llm.advisor_guaranteed_fact_comparison import guaranteed_facts_from_exact_outcome, guaranteed_facts_from_normal_formula_interval, guaranteed_facts_from_water_gun_interval, rank_guaranteed_candidates

def run_detached_strategy_orchestration(*,decision_state:Mapping[str,Any],decision_owner:Mapping[str,Any],selection_snapshot:Mapping[str,Any],execution_bundle:Mapping[str,Any],predictive_attacks:Mapping[str,Mapping[str,Any]]|None=None,water_gun_inputs:Mapping[str,Any]|None=None,normal_formula_inputs:Mapping[str,Mapping[str,Any]]|None=None)->dict[str,Any]:
 """Route independently supported candidates without becoming a state owner."""
 if not _d0(decision_owner,selection_snapshot,execution_bundle):return {"status":"rejected","reason":"orchestration_d0_mismatch"}
 discovered=discover_candidates(snapshot=selection_snapshot)
 if discovered.get("status")!="resolved":return discovered
 enriched=enrich_discovered_candidates(selection_snapshot=selection_snapshot,execution_bundle=execution_bundle,candidates=discovered["candidates"])
 if enriched.get("status")!="resolved":return enriched
 evidence=[]; facts=[]; attacks=predictive_attacks or {}; normal=dict(normal_formula_inputs or {}); water=water_gun_inputs or {}; legacy_water="attack:water-gun" not in normal and isinstance(water,Mapping)
 if legacy_water: normal["attack:water-gun"]=water
 for candidate in enriched["candidates"]:
  cid=candidate["candidate_id"]
  if cid=="attack:seismic-toss" and isinstance(attacks.get(cid),Mapping):
   bound=enrich_predictive_attack_candidate(candidate=candidate,predictive_authority=attacks[cid])
   if bound.get("status")=="resolved":
    outcome=materialize_predictive_fixed_damage_outcome(decision_state=decision_state,decision_owner=decision_owner,candidate=bound["candidate"],predictive_authority=attacks[cid])
    if outcome.get("status")=="complete":
     fact=guaranteed_facts_from_exact_outcome(decision_owner=decision_owner,outcome=outcome["outcome"]);evidence.append(_e(candidate,"exact_outcome",outcome=outcome["outcome"],facts=fact));facts.append(fact);continue
  normal_input=normal.get(cid)
  if candidate["action_type"]=="attack" and isinstance(normal_input,Mapping) and all(isinstance(normal_input.get(key),Mapping) for key in ("target_owner","snapshot_damage_input","stat_provenance")):
   interval=(build_predictive_water_gun_interval if cid=="attack:water-gun" and legacy_water else build_predictive_normal_formula_interval)(branch_state=decision_state,decision_owner=decision_owner,target_owner=normal_input.get("target_owner"),snapshot_damage_input=normal_input.get("snapshot_damage_input"),stat_provenance=normal_input.get("stat_provenance"),trusted_level=normal_input.get("trusted_level"))
   if interval.get("completeness")=="exact_complete":
    own=decision_state["active"][decision_owner["side"]]["current_hp"];fact=(guaranteed_facts_from_water_gun_interval if cid=="attack:water-gun" and legacy_water else guaranteed_facts_from_normal_formula_interval)(candidate=candidate,interval=interval,own_current_hp=own);evidence.append(_e(candidate,"guaranteed_facts",interval=interval,facts=fact));facts.append(fact);continue
  if candidate["action_type"]=="manual_switch":
   outcome=materialize_candidates(decision_state=decision_state,decision_owner=decision_owner,candidates=[candidate])["outcomes"][0]
   if outcome.get("status")=="complete":
    fact=guaranteed_facts_from_exact_outcome(decision_owner=decision_owner,outcome=outcome["outcome"]);evidence.append(_e(candidate,"exact_outcome",outcome=outcome["outcome"],facts=fact));facts.append(fact);continue
  evidence.append(_e(candidate,"incomplete",reason=candidate.get("execution_reason","observation_required")))
 ranking=rank_guaranteed_candidates(candidates=facts) if len(facts)>=2 else {"status":"incomplete_comparison_set","preferred_frontier":[x["candidate_id"] for x in evidence if x["evidence_class"]!="incomplete"],"reason":"fewer_than_two_comparable_candidates"}
 return {"schema_version":"deterministic-strategy-orchestration-result-v1","status":ranking["status"],"session_id":decision_owner["session_id"],"decision_branch_fingerprint":selection_snapshot["decision_branch_fingerprint"],"decision_owner":decision_owner,"selection_completeness":discovered["candidate_set_completeness"],"candidates":evidence,"ranking":ranking,"provenance":"detached_strategy_orchestration_v1"}
def _e(c,kind,**extra):return {"schema_version":"deterministic-strategy-candidate-evidence-v1","candidate_id":c["candidate_id"],"action_type":c["action_type"],"evidence_class":kind,"execution_readiness":c.get("execution_readiness"),**extra}
def _d0(o,s,e):return isinstance(o,Mapping) and all(s.get(k)==e.get(k) for k in ("session_id","decision_branch_fingerprint","decision_owner")) and s.get("decision_owner")==dict(o)
