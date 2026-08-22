from llm.advisor_guaranteed_fact_comparison import compare_guaranteed_candidates,rank_guaranteed_candidates
O={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}
def f(cid,own=False,foe=None,hp=80,possible=False):return {"status":"resolved","schema_version":"deterministic-guaranteed-candidate-facts-v1","candidate_id":cid,"action_type":"attack","session_id":"s","source_branch_fingerprint":"f","decision_owner":O,"horizon":"immediate_action_consequence","evidence_class":"test","guaranteed_own_fainted":own,"guaranteed_opponent_fainted":foe,"exact_own_hp":hp,"possible_opponent_ko":possible,"substitute_facts":{},"provenance":"test"}
def test_guaranteed_rules_possible_ko_and_order_invariance():
 a,b,c=f("a",foe=True),f("b",foe=False),f("c",foe=None,possible=True)
 assert compare_guaranteed_candidates(candidate_a=a,candidate_b=b)["preferred_candidate"]=="a"
 assert compare_guaranteed_candidates(candidate_a=c,candidate_b=b)["comparison"]=="tied_on_supported_facts"
 assert rank_guaranteed_candidates(candidates=[a,b,c])["preferred_frontier"]==rank_guaranteed_candidates(candidates=[c,b,a])["preferred_frontier"]
def test_scope_and_own_hp_guards():
 a,b=f("a",hp=90),f("b",hp=80)
 assert compare_guaranteed_candidates(candidate_a=a,candidate_b=b)["reason"]=="safer_exact_self_hp"
 assert compare_guaranteed_candidates(candidate_a=a,candidate_b={**b,"source_branch_fingerprint":"other"})["status"]=="rejected"
