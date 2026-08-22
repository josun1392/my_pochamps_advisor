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
