from copy import deepcopy
from llm.advisor_strategy_explanation import explain_detached_strategy
O={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}
def _r(status="resolved",selection="complete"):
 return {"schema_version":"deterministic-strategy-orchestration-result-v1","status":status,"session_id":"s","decision_branch_fingerprint":"f","decision_owner":O,"selection_completeness":selection,"candidates":[{"candidate_id":"attack:water-gun","action_type":"attack","evidence_class":"guaranteed_facts","execution_readiness":"interval_ready","facts":{"possible_target_KO":True}},{"candidate_id":"manual_switch:x","action_type":"manual_switch","evidence_class":"exact_outcome","facts":{"guaranteed_target_survival":True}},{"candidate_id":"attack:tackle","action_type":"attack","evidence_class":"incomplete","reason":"observation_required"}],"ranking":{"status":status,"preferred_frontier":["manual_switch:x"],"pairwise_matrix":[{"comparison":"preferred","preferred_candidate":"manual_switch:x","reason":"avoids_self_ko"}]}}
def test_structured_explanation_preserves_frontier_uncertainty_reasons_and_purity():
 r=_r();before=deepcopy(r);x=explain_detached_strategy(orchestration=r);assert r==before and x["overall_status"]=="resolved" and x["horizon"]=="immediate_action_consequence" and x["preferred_frontier"]==["manual_switch:x"]
 rows={z["candidate_id"]:z for z in x["candidates"]};assert rows["attack:water-gun"]["guaranteed_facts"]["possible_target_KO"] and rows["attack:tackle"]["incomplete_reason"]=="observation_required" and rows["manual_switch:x"]["comparison_reasons"]==["avoids_self_ko"] and explain_detached_strategy(orchestration=r)==x
def test_tie_selection_incomplete_and_malformed_reject():
 tie=_r(status="tied_preferred_set");tie["ranking"]["preferred_frontier"]=["attack:water-gun","manual_switch:x"];assert len(explain_detached_strategy(orchestration=tie)["preferred_frontier"])==2
 assert explain_detached_strategy(orchestration=_r(selection="partial"))["overall_status"]=="selection_incomplete"
 assert explain_detached_strategy(orchestration={})["status"]=="rejected"
