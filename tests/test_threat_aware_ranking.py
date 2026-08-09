from llm.advisor_candidate_contract import rank_direct_mechanics_candidates
from llm.advisor_threat_ranking import project_threat_ranking_tier

def _candidate(slot, move, damage=10):
 return {"slot_index":slot,"move":move,"status":"resolved","availability":"usable","mechanics_result":{"status":"known","mechanics_source":"native_q12_direct_damage","damage_range":{"minimum":damage,"maximum":damage},"damage_percent_range":{"minimum":damage,"maximum":damage},"ko_result":{"single_hit_probability":0.0},"type_effectiveness":1.0}}
def _summary(**override):
 base={"known_guaranteed_ohko_capability_exists":False,"known_executed_guaranteed_ohko_threat_exists":False,"known_executed_possible_ohko_threat_exists":False,"candidate_set_complete":False,"known_candidate_count":0,"unknown_slots_remaining":4,"known_threat_evaluation_complete":False,"global_threat_complete":False,"all_known_actions_preempted":"unresolved","no_known_guaranteed_ohko":"unresolved"}; return {**base,**override}

def test_projector_enforces_six_tiers_and_partial_positive_only_boundary():
 assert project_threat_ranking_tier(_summary(known_executed_guaranteed_ohko_threat_exists=True))[1]==0
 assert project_threat_ranking_tier(_summary(known_guaranteed_ohko_capability_exists=True))[1]==1
 assert project_threat_ranking_tier(_summary(known_executed_possible_ohko_threat_exists=True))[1]==2
 assert project_threat_ranking_tier(_summary(no_known_guaranteed_ohko="true",all_known_actions_preempted="true"))[1]==3
 complete=_summary(candidate_set_complete=True,known_candidate_count=4,unknown_slots_remaining=0,known_threat_evaluation_complete=True,global_threat_complete=True,no_known_guaranteed_ohko="true")
 assert project_threat_ranking_tier(complete)[1]==4
 assert project_threat_ranking_tier({**complete,"all_known_actions_preempted":"true"})[1]==5

def test_threat_tier_reorders_before_base_rank_but_same_tier_keeps_base_and_stable_order():
 candidates=[_candidate(0,"strong",20),_candidate(1,"weak",10)]
 threats={"self:0:strong":_summary(known_executed_guaranteed_ohko_threat_exists=True),"self:1:weak":_summary()}
 ranked=rank_direct_mechanics_candidates(candidates=candidates,threat_summaries=threats)
 assert ranked[(1,"weak")]["rank"]==1 and ranked[(0,"strong")]["rank"]==2
 neutral=rank_direct_mechanics_candidates(candidates=candidates,threat_summaries={"self:0:strong":_summary(),"self:1:weak":_summary()})
 assert neutral[(0,"strong")]["rank"]==1
 ties=rank_direct_mechanics_candidates(candidates=[_candidate(0,"a"),_candidate(1,"b")],threat_summaries={"self:0:a":_summary(),"self:1:b":_summary()})
 assert ties[(0,"a")]["rank"]==1

def test_probability_is_ignored_and_malformed_present_summary_fails_closed():
 candidate=_candidate(0,"move")
 first=rank_direct_mechanics_candidates(candidates=[candidate],threat_summaries={"self:0:move":_summary(known_executed_possible_ohko_threat_exists=True,ko_by_1={"numerator":9,"denominator":10})})
 second=rank_direct_mechanics_candidates(candidates=[candidate],threat_summaries={"self:0:move":_summary(known_executed_possible_ohko_threat_exists=True,ko_by_1={"numerator":1,"denominator":10})})
 assert first==second
 import pytest
 with pytest.raises(ValueError): rank_direct_mechanics_candidates(candidates=[candidate],threat_summaries={"self:0:move":{}})
