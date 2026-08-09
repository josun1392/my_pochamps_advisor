from copy import deepcopy

from llm.advisor_known_threat_reducer import reduce_known_opponent_threats


def _self(slot=0): return {"slot_index":slot,"move":f"move-{slot}"}
def _pair(self_id, ohko="no", *, preempted=False, complete=True, first=False):
 return {"self_candidate_id":self_id,"pair_mechanical_completeness":complete,"pair_supportability":"complete" if complete else "unsupported_mechanic","opponent_move_success":{"status":"allowed"},"opponent_ohko_result":ohko,"opponent_action_preemption_status":"preempted" if preempted else "executable","self_action_preemption_status":"executable","action_order_result":{"status":"acts_second" if first else "acts_first"}}
def _set(pairs, *, state="partially_known", complete=False, count=None, unknown=2):
 return {"opponent_known_move_state":state,"known_candidate_count":len(pairs) if count is None else count,"opponent_candidate_set_complete":complete,"unknown_slots_remaining":unknown,"pairs":pairs}


def test_unknown_and_partial_sets_preserve_tri_state_and_known_global_separation():
 unknown=reduce_known_opponent_threats(pair_set=_set([],state="unknown",unknown=4),self_candidates=[_self()])["threat_summaries"][0]
 partial=reduce_known_opponent_threats(pair_set=_set([_pair("self:0:move-0"),_pair("self:0:move-0")]),self_candidates=[_self()])["threat_summaries"][0]
 assert unknown["known_pair_count"]==0 and unknown["all_known_actions_preempted"]=="unresolved"
 assert partial["known_threat_evaluation_complete"] is True and partial["global_threat_complete"] is False
 assert partial["no_known_guaranteed_ohko"]=="true"


def test_raw_capability_and_executed_threat_remain_separate_after_self_preemption():
 summary=reduce_known_opponent_threats(pair_set=_set([_pair("self:0:move-0","guaranteed",preempted=True)]),self_candidates=[_self()])["threat_summaries"][0]
 assert summary["known_guaranteed_ohko_capability_exists"] is True
 assert summary["known_executed_guaranteed_ohko_threat_exists"] is False
 assert summary["self_preempts_count"]==1 and summary["all_known_actions_preempted"]=="true"


def test_complete_incomplete_set_preserves_positive_facts_but_withholds_universal_negative():
 pairs=[_pair("self:0:move-0","guaranteed"),_pair("self:0:move-0",complete=False),_pair("self:0:move-0"),_pair("self:0:move-0")]
 summary=reduce_known_opponent_threats(pair_set=_set(pairs,state="complete",complete=True,count=4,unknown=0),self_candidates=[_self()])["threat_summaries"][0]
 assert summary["known_guaranteed_ohko_capability_exists"] is True
 assert summary["no_known_guaranteed_ohko"]=="false"
 assert summary["known_threat_evaluation_complete"] is False and summary["global_threat_complete"] is False


def test_per_self_summary_is_detached_and_never_aggregates_probability_or_cross_self_pairs():
 pairs=[_pair("self:0:move-0","possible"),_pair("self:1:move-1","guaranteed",first=True)]
 source=deepcopy(pairs); summaries=reduce_known_opponent_threats(pair_set=_set(pairs),self_candidates=[_self(0),_self(1)])["threat_summaries"]
 assert [row["known_pair_count"] for row in summaries]==[1,1]
 assert "aggregate_probability" not in summaries[0]
 summaries[0]["known_pair_count"]=99
 assert pairs==source
