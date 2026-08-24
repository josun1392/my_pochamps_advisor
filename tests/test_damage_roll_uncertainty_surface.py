from llm.advisor_strategy_explanation import explain_detached_strategy
from ui.strategy_explanation_presentation import present_strategy_explanation

O={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}
def test_roll_summary_is_leaf_local_and_keeps_exact_ko_count_and_multiplicity():
 ledger={"outcomes":tuple({"damage":damage} for damage in (9,9,10,10,10,10,10,10,10,10,10,10,10,10,10,10)),"critical_scope":"non_critical_assumed","damage_value_multiplicity":({"damage":9,"numerator":2,"denominator":16},{"damage":10,"numerator":14,"denominator":16})}
 critical={"status":"resolved","schema_version":"deterministic-predictive-critical-hit-uncertainty-v1","move_id":"tackle","critical_probability":{"numerator":1,"denominator":24},"branches":({"branch":"non_critical","consequences":{"damage_roll_uncertainty":ledger,"interval":{"target_hp_before":10}}},{"branch":"critical","consequences":{"damage_roll_uncertainty":ledger,"interval":{"target_hp_before":10}}})}
 hit={"status":"resolved","schema_version":"deterministic-predictive-hit-miss-uncertainty-v1","move_id":"tackle","probability_percent":80,"branches":({"branch":"hit","consequences":{"critical_hit_uncertainty":critical}},{"branch":"miss","consequences":{}}),"guaranteed_facts":{}}
 orchestration={"schema_version":"deterministic-strategy-orchestration-result-v1","status":"resolved","session_id":"s","decision_branch_fingerprint":"f","decision_owner":O,"selection_completeness":"complete","candidates":[{"candidate_id":"attack:tackle","action_type":"attack","evidence_class":"hit_miss_uncertainty","facts":{"possible_opponent_ko":True},"uncertainty":hit}],"ranking":{"status":"resolved","preferred_frontier":["attack:tackle"],"pairwise_matrix":[]}}
 explanation=explain_detached_strategy(orchestration=orchestration); row=explanation["candidates"][0]
 assert row["damage_roll_summaries"][0]["conditional_ko_probability"]=={"numerator":14,"denominator":16}
 assert row["damage_roll_summaries"][0]["damage_value_multiplicity"][0]["numerator"]==2
 presentation=present_strategy_explanation(explanation=explanation)
 assert "KO 14/16" in presentation["candidates"][0]["uncertainty_labels"][-2]
