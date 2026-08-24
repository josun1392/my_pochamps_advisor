from copy import deepcopy
import llm.advisor_detached_strategy_orchestration as subject

O={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}; S={"status":"resolved","session_id":"s","decision_branch_fingerprint":"f","decision_owner":O}; E={**S,"schema_version":"deterministic-current-execution-authority-v1"}
def _c(cid,kind="attack"):return {"schema_version":"deterministic-action-candidate-v1","candidate_id":cid,"action_type":kind,"decision_owner":O,"source_branch_fingerprint":"f","execution_readiness":"execution_incomplete"}
def test_global_d0_mismatch_rejects():
 assert subject.run_detached_strategy_orchestration(decision_state={},decision_owner=O,selection_snapshot=S,execution_bundle={**E,"session_id":"other"})["status"]=="rejected"
def test_mixed_evidence_routing_is_pure_and_preserves_incomplete(monkeypatch):
 candidates=[_c("attack:seismic-toss"),_c("attack:water-gun"),_c("manual_switch:x","manual_switch"),_c("attack:tackle")]
 monkeypatch.setattr(subject,"discover_candidates",lambda **_: {"status":"resolved","candidates":deepcopy(candidates),"candidate_set_completeness":"complete"})
 monkeypatch.setattr(subject,"enrich_discovered_candidates",lambda **_: {"status":"resolved","candidates":deepcopy(candidates)})
 monkeypatch.setattr(subject,"enrich_predictive_attack_candidate",lambda **k:{"status":"resolved","candidate":k["candidate"]})
 monkeypatch.setattr(subject,"materialize_predictive_fixed_damage_outcome",lambda **_:{"status":"complete","outcome":{"candidate_id":"attack:seismic-toss"}})
 monkeypatch.setattr(subject,"materialize_candidates",lambda **_:{"outcomes":[{"status":"complete","outcome":{"candidate_id":"manual_switch:x"}}]})
 monkeypatch.setattr(subject,"guaranteed_facts_from_exact_outcome",lambda **k:{"status":"resolved","candidate_id":k["outcome"]["candidate_id"]})
 monkeypatch.setattr(subject,"build_predictive_water_gun_interval",lambda **_:{"completeness":"exact_complete"})
 monkeypatch.setattr(subject,"guaranteed_facts_from_water_gun_interval",lambda **k:{"status":"resolved","candidate_id":k["candidate"]["candidate_id"]})
 monkeypatch.setattr(subject,"rank_guaranteed_candidates",lambda **k:{"status":"resolved","preferred_frontier":["attack:seismic-toss"],"pairwise_matrix":k["candidates"]})
 root={"active":{"self":{"current_hp":90}}}; before=deepcopy(root)
 result=subject.run_detached_strategy_orchestration(decision_state=root,decision_owner=O,selection_snapshot=S,execution_bundle=E,predictive_attacks={"attack:seismic-toss":{}},water_gun_inputs={"target_owner":{},"snapshot_damage_input":{},"stat_provenance":{},"trusted_level":50})
 assert root==before and {x["candidate_id"]:x["evidence_class"] for x in result["candidates"]}=={"attack:seismic-toss":"exact_outcome","attack:water-gun":"guaranteed_facts","manual_switch:x":"exact_outcome","attack:tackle":"incomplete"}


def test_explicit_strict_hit_authority_routes_normal_hit_consequence_through_uncertainty(monkeypatch):
 candidate=_c("attack:water-gun")
 monkeypatch.setattr(subject,"discover_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)],"candidate_set_completeness":"complete"})
 monkeypatch.setattr(subject,"enrich_discovered_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)]})
 monkeypatch.setattr(subject,"build_predictive_water_gun_interval",lambda **_: {"completeness":"exact_complete"})
 fact={"status":"resolved","candidate_id":"attack:water-gun"}
 monkeypatch.setattr(subject,"guaranteed_facts_from_water_gun_interval",lambda **_: deepcopy(fact))
 def branch(**kwargs):
  assert kwargs["strict_hit_probability"]=={"status":"resolved","marker":"strict"}
  assert kwargs["hit_consequences"]["guaranteed_facts"]==fact
  return {"status":"resolved","branches":(),"guaranteed_facts":{**fact,"marker":"intersection"}}
 monkeypatch.setattr(subject,"compose_predictive_hit_miss_uncertainty",branch)
 root={"active":{"self":{"current_hp":90},"opponent":{"current_hp":100}}}
 result=subject.run_detached_strategy_orchestration(decision_state=root,decision_owner=O,selection_snapshot=S,execution_bundle=E,water_gun_inputs={"target_owner":{},"snapshot_damage_input":{},"stat_provenance":{},"trusted_level":50},hit_probability_authorities={"attack:water-gun":{"status":"resolved","marker":"strict"}})
 assert result["candidates"][0]["evidence_class"]=="hit_miss_uncertainty"
 assert result["candidates"][0]["facts"]["marker"]=="intersection"


def test_critical_authority_nests_critical_leaves_inside_existing_hit_branch(monkeypatch):
 candidate=_c("attack:tackle")
 monkeypatch.setattr(subject,"discover_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)],"candidate_set_completeness":"complete"})
 monkeypatch.setattr(subject,"enrich_discovered_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)]})
 normal={"completeness":"exact_complete","scope":{"critical":"non_critical_assumed"}}
 critical={"completeness":"exact_complete","scope":{"critical":"critical_assumed"}}
 monkeypatch.setattr(subject,"build_predictive_normal_formula_interval",lambda **_: deepcopy(normal))
 monkeypatch.setattr(subject,"materialize_predictive_critical_damage_contexts",lambda **_: {"status":"resolved","critical_context":deepcopy(critical)})
 fact={"status":"resolved","candidate_id":"attack:tackle"}
 monkeypatch.setattr(subject,"guaranteed_facts_from_normal_formula_interval",lambda **_: deepcopy(fact))
 def compose_crit(**kwargs):
  assert kwargs["non_critical_consequences"]["interval"]==normal
  assert kwargs["critical_consequences"]["interval"]==critical
  return {"status":"resolved","guaranteed_facts":{**fact,"marker":"critical_intersection"},"branches":("non_critical","critical")}
 monkeypatch.setattr(subject,"compose_predictive_critical_hit_uncertainty",compose_crit)
 def compose_hit(**kwargs):
  assert kwargs["hit_consequences"]["critical_hit_uncertainty"]["branches"]==("non_critical","critical")
  return {"status":"resolved","branches":(),"guaranteed_facts":{**fact,"marker":"hit_miss_intersection"}}
 monkeypatch.setattr(subject,"compose_predictive_hit_miss_uncertainty",compose_hit)
 root={"active":{"self":{"current_hp":90},"opponent":{"current_hp":100}}}
 result=subject.run_detached_strategy_orchestration(decision_state=root,decision_owner=O,selection_snapshot=S,execution_bundle=E,normal_formula_inputs={"attack:tackle":{"target_owner":{},"snapshot_damage_input":{},"stat_provenance":{},"trusted_level":50}},hit_probability_authorities={"attack:tackle":{"status":"resolved"}},critical_hit_probability_authorities={"attack:tackle":{"status":"resolved"}})
 assert result["candidates"][0]["evidence_class"]=="hit_miss_uncertainty"
 assert result["candidates"][0]["facts"]["marker"]=="hit_miss_intersection"


def test_resolved_probabilistic_self_stage_authority_stays_inside_hit_consequences(monkeypatch):
 candidate=_c("attack:metal-claw")
 monkeypatch.setattr(subject,"discover_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)],"candidate_set_completeness":"complete"})
 monkeypatch.setattr(subject,"enrich_discovered_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)]})
 interval={"completeness":"exact_complete","scope":{"critical":"non_critical_assumed"}}
 monkeypatch.setattr(subject,"build_predictive_normal_formula_interval",lambda **_: deepcopy(interval))
 fact={"status":"resolved","candidate_id":"attack:metal-claw"}
 monkeypatch.setattr(subject,"guaranteed_facts_from_normal_formula_interval",lambda **_: deepcopy(fact))
 secondary={"status":"resolved","branches":[{"branch":"no_effect"},{"branch":"effect"}],"effect_probability":{"numerator":10,"denominator":100}}
 def compose_secondary(**kwargs):
  assert kwargs["candidate"]["candidate_id"]=="attack:metal-claw"
  assert kwargs["interval"]==interval and kwargs["runtime_authority"]=={"status":"resolved","marker":"metal_claw"}
  return deepcopy(secondary)
 monkeypatch.setattr(subject,"compose_predictive_probabilistic_self_stage_effect_uncertainty",compose_secondary)
 def compose_hit(**kwargs):
  assert kwargs["hit_consequences"]["probabilistic_self_stage_effect_uncertainty"]==secondary
  return {"status":"resolved","branches":(),"guaranteed_facts":{**fact,"marker":"hit_intersection"}}
 monkeypatch.setattr(subject,"compose_predictive_hit_miss_uncertainty",compose_hit)
 root={"active":{"self":{"current_hp":90},"opponent":{"current_hp":100}}}
 result=subject.run_detached_strategy_orchestration(decision_state=root,decision_owner=O,selection_snapshot=S,execution_bundle=E,normal_formula_inputs={"attack:metal-claw":{"target_owner":{},"snapshot_damage_input":{},"stat_provenance":{},"trusted_level":50}},hit_probability_authorities={"attack:metal-claw":{"status":"resolved"}},probabilistic_self_stage_effect_authorities={"attack:metal-claw":{"status":"resolved","marker":"metal_claw"}})
 assert result["candidates"][0]["facts"]["marker"]=="hit_intersection"


def test_metal_claw_missing_probabilistic_authority_fails_closed(monkeypatch):
 candidate=_c("attack:metal-claw")
 monkeypatch.setattr(subject,"discover_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)],"candidate_set_completeness":"complete"})
 monkeypatch.setattr(subject,"enrich_discovered_candidates",lambda **_: {"status":"resolved","candidates":[deepcopy(candidate)]})
 monkeypatch.setattr(subject,"build_predictive_normal_formula_interval",lambda **_: {"completeness":"exact_complete"})
 monkeypatch.setattr(subject,"rank_guaranteed_candidates",lambda **k: {"status":"resolved","preferred_frontier":(),"pairwise_matrix":()})
 root={"active":{"self":{"current_hp":90},"opponent":{"current_hp":100}}}
 result=subject.run_detached_strategy_orchestration(decision_state=root,decision_owner=O,selection_snapshot=S,execution_bundle=E,normal_formula_inputs={"attack:metal-claw":{"target_owner":{},"snapshot_damage_input":{},"stat_provenance":{},"trusted_level":50}})
 assert result["candidates"][0]["evidence_class"]=="incomplete"
 assert result["candidates"][0]["reason"]=="probabilistic_self_stage_effect_authority_missing"
