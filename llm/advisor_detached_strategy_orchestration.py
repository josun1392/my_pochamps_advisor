"""Pure coordinator for the bounded detached strategy components."""
from typing import Any, Mapping
from llm.advisor_current_state_candidate_discovery import discover_candidates
from llm.advisor_current_execution_authority import enrich_discovered_candidates
from llm.advisor_candidate_outcome_materialization import materialize_candidates
from llm.advisor_predictive_fixed_damage_outcome import enrich_predictive_attack_candidate, materialize_predictive_fixed_damage_outcome
from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval
from llm.advisor_predictive_water_gun_interval import build_predictive_water_gun_interval
from llm.advisor_predictive_normal_formula_post_hit import compose_predictive_normal_formula_post_hit
from llm.advisor_predictive_deterministic_stage_effects import compose_predictive_deterministic_stage_effects
from llm.advisor_predictive_hit_miss_uncertainty import compose_predictive_hit_miss_uncertainty
from llm.advisor_predictive_critical_damage_context import materialize_predictive_critical_damage_contexts
from llm.advisor_predictive_critical_hit_uncertainty import compose_predictive_critical_hit_uncertainty
from llm.advisor_guaranteed_fact_comparison import guaranteed_facts_from_exact_outcome, guaranteed_facts_from_normal_formula_interval, guaranteed_facts_from_water_gun_interval, rank_guaranteed_candidates

def run_detached_strategy_orchestration(*,decision_state:Mapping[str,Any],decision_owner:Mapping[str,Any],selection_snapshot:Mapping[str,Any],execution_bundle:Mapping[str,Any],predictive_attacks:Mapping[str,Mapping[str,Any]]|None=None,water_gun_inputs:Mapping[str,Any]|None=None,normal_formula_inputs:Mapping[str,Mapping[str,Any]]|None=None,post_hit_inputs:Mapping[str,Mapping[str,Any]]|None=None,hit_probability_authorities:Mapping[str,Mapping[str,Any]]|None=None,critical_hit_probability_authorities:Mapping[str,Mapping[str,Any]]|None=None)->dict[str,Any]:
 """Route independently supported candidates without becoming a state owner."""
 if not _d0(decision_owner,selection_snapshot,execution_bundle):return {"status":"rejected","reason":"orchestration_d0_mismatch"}
 discovered=discover_candidates(snapshot=selection_snapshot)
 if discovered.get("status")!="resolved":return discovered
 enriched=enrich_discovered_candidates(selection_snapshot=selection_snapshot,execution_bundle=execution_bundle,candidates=discovered["candidates"])
 if enriched.get("status")!="resolved":return enriched
 evidence=[]; facts=[]; attacks=predictive_attacks or {}; normal=dict(normal_formula_inputs or {}); post=dict(post_hit_inputs or {}); hit_probabilities=hit_probability_authorities or {}; critical_probabilities=critical_hit_probability_authorities or {}; water=water_gun_inputs or {}; legacy_water="attack:water-gun" not in normal and isinstance(water,Mapping)
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
    own=decision_state["active"][decision_owner["side"]]["current_hp"]; post_input=post.get(cid)
    if not isinstance(post_input,Mapping) and isinstance(normal_input.get("post_hit_authority"),Mapping): post_input={"move_metadata":normal_input.get("move_metadata",{}),**normal_input["post_hit_authority"]}
    fact=_normal_formula_facts(candidate,interval,own,post_input,normal_input,legacy_water=cid=="attack:water-gun" and legacy_water)
    hit_consequences={"interval":interval,"post_hit":fact.get("post_hit"),"stage_effects":fact.get("stage_effects"),"guaranteed_facts":fact}
    critical_probability=critical_probabilities.get(cid)
    if isinstance(critical_probability,Mapping):
     if critical_probability.get("status")!="resolved": evidence.append(_e(candidate,"incomplete",reason=critical_probability.get("reason","strict_critical_hit_probability_unavailable"),critical_hit_probability=critical_probability));continue
     paired=materialize_predictive_critical_damage_contexts(branch_state=decision_state,decision_owner=decision_owner,target_owner=normal_input.get("target_owner"),snapshot_damage_input=normal_input.get("snapshot_damage_input"),stat_provenance=normal_input.get("stat_provenance"),trusted_level=normal_input.get("trusted_level"))
     if paired.get("status")!="resolved": evidence.append(_e(candidate,"incomplete",reason=paired.get("reason","critical_damage_context_unavailable"),critical_damage_context=paired));continue
     critical_interval=paired["critical_context"]
     critical_fact=_normal_formula_facts(candidate,critical_interval,own,post_input,normal_input)
     critical_uncertainty=compose_predictive_critical_hit_uncertainty(candidate=candidate,strict_critical_hit_probability=critical_probability,paired_damage_contexts=paired,non_critical_consequences=hit_consequences,critical_consequences={"interval":critical_interval,"post_hit":critical_fact.get("post_hit"),"stage_effects":critical_fact.get("stage_effects"),"guaranteed_facts":critical_fact})
     if critical_uncertainty.get("status")!="resolved": evidence.append(_e(candidate,"incomplete",reason=critical_uncertainty.get("reason","strict_critical_hit_probability_unavailable"),critical_hit_probability=critical_uncertainty));continue
     fact=critical_uncertainty["guaranteed_facts"]
     hit_consequences={"critical_hit_uncertainty":critical_uncertainty,"guaranteed_facts":fact}
    probability=hit_probabilities.get(cid)
    if isinstance(probability,Mapping):
     uncertainty=compose_predictive_hit_miss_uncertainty(candidate=candidate,strict_hit_probability=probability,hit_consequences=hit_consequences,miss_baseline={"attacker_current_hp":own,"target_current_hp":decision_state["active"]["opponent" if decision_owner["side"]=="self" else "self"].get("current_hp")})
     if uncertainty.get("status")=="resolved": evidence.append(_e(candidate,"hit_miss_uncertainty",uncertainty=uncertainty,facts=uncertainty["guaranteed_facts"]));facts.append(uncertainty["guaranteed_facts"]);continue
     evidence.append(_e(candidate,"incomplete",reason=uncertainty.get("reason","strict_hit_probability_unavailable"),hit_probability=uncertainty));continue
    evidence.append(_e(candidate,"guaranteed_facts",interval=interval,facts=fact));facts.append(fact);continue
  if candidate["action_type"]=="manual_switch":
   outcome=materialize_candidates(decision_state=decision_state,decision_owner=decision_owner,candidates=[candidate])["outcomes"][0]
   if outcome.get("status")=="complete":
    fact=guaranteed_facts_from_exact_outcome(decision_owner=decision_owner,outcome=outcome["outcome"]);evidence.append(_e(candidate,"exact_outcome",outcome=outcome["outcome"],facts=fact));facts.append(fact);continue
  evidence.append(_e(candidate,"incomplete",reason=candidate.get("execution_reason","observation_required")))
 ranking=rank_guaranteed_candidates(candidates=facts) if len(facts)>=2 else {"status":"incomplete_comparison_set","preferred_frontier":[x["candidate_id"] for x in evidence if x["evidence_class"]!="incomplete"],"reason":"fewer_than_two_comparable_candidates"}
 return {"schema_version":"deterministic-strategy-orchestration-result-v1","status":ranking["status"],"session_id":decision_owner["session_id"],"decision_branch_fingerprint":selection_snapshot["decision_branch_fingerprint"],"decision_owner":decision_owner,"selection_completeness":discovered["candidate_set_completeness"],"candidates":evidence,"ranking":ranking,"provenance":"detached_strategy_orchestration_v1"}
def _e(c,kind,**extra):return {"schema_version":"deterministic-strategy-candidate-evidence-v1","candidate_id":c["candidate_id"],"action_type":c["action_type"],"evidence_class":kind,"execution_readiness":c.get("execution_readiness"),**extra}
def _d0(o,s,e):return isinstance(o,Mapping) and all(s.get(k)==e.get(k) for k in ("session_id","decision_branch_fingerprint","decision_owner")) and s.get("decision_owner")==dict(o)
def _normal_formula_facts(candidate,interval,own,post_input,normal_input,legacy_water=False):
 fact=(guaranteed_facts_from_water_gun_interval if legacy_water else guaranteed_facts_from_normal_formula_interval)(candidate=candidate,interval=interval,own_current_hp=own)
 if isinstance(post_input,Mapping):
  composed=compose_predictive_normal_formula_post_hit(interval=interval,move_metadata=post_input.get("move_metadata",{}),attacker_hp=post_input.get("attacker_hp",{}),attacker_item=post_input.get("attacker_item"),attacker_ability=post_input.get("attacker_ability"),target_ability=post_input.get("target_ability"),attacker_item_known=post_input.get("attacker_item_known",True))
  if composed.get("status")=="resolved": fact={**fact,"guaranteed_own_fainted":composed["guaranteed_attacker_faint"],"exact_own_hp":composed["attacker_post_hit_hp_values"][0] if len(composed["attacker_post_hit_hp_values"])==1 else None,"possible_own_faint":composed["possible_attacker_faint"],"post_hit":composed}
 stage=compose_predictive_deterministic_stage_effects(interval=interval,stage_effect_authority=normal_input.get("stage_effect_authority",{}),stat_provenance=normal_input.get("stat_provenance",{}))
 return {**fact,"stage_effects":stage} if stage.get("status")=="resolved" else fact
