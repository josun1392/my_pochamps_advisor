"""Design-only T1 policy matrix; production ranking is deliberately unchanged."""


def _tier(summary):
    if summary.get("known_executed_guaranteed_ohko_threat_exists"): return "executed_guaranteed_ohko", 0
    if summary.get("known_guaranteed_ohko_capability_exists"): return "unresolved_guaranteed_ohko_exposure", 1
    if summary.get("known_executed_possible_ohko_threat_exists"): return "executed_possible_ohko", 2
    if summary.get("global_threat_complete") and summary.get("all_known_actions_preempted") == "true": return "complete_set_all_actions_preempted", 5
    if summary.get("global_threat_complete") and summary.get("no_known_guaranteed_ohko") == "true": return "complete_set_no_guaranteed_ohko", 4
    return "neutral_no_positive_threat_evidence", 3


def test_unknown_and_partial_absence_of_danger_are_neutral_not_safety_rewards():
    unknown={}; partial={"known_threat_evaluation_complete":True,"no_known_guaranteed_ohko":"true","global_threat_complete":False,"all_known_actions_preempted":"true"}
    assert _tier(unknown)==("neutral_no_positive_threat_evidence",3)
    assert _tier(partial)==("neutral_no_positive_threat_evidence",3)


def test_partial_confirmed_danger_penalizes_without_declaring_other_candidate_safe():
    danger={"known_executed_guaranteed_ohko_threat_exists":True,"global_threat_complete":False}
    neutral={"global_threat_complete":False}
    assert _tier(danger)[1] < _tier(neutral)[1]
    assert _tier(neutral)[0]=="neutral_no_positive_threat_evidence"


def test_executed_guaranteed_is_stronger_than_unresolved_raw_and_possible_ko():
    executed={"known_executed_guaranteed_ohko_threat_exists":True}
    raw={"known_guaranteed_ohko_capability_exists":True}
    possible={"known_executed_possible_ohko_threat_exists":True}
    assert _tier(executed)[1] < _tier(raw)[1] < _tier(possible)[1]


def test_complete_mechanically_complete_negative_evidence_only_can_create_bounded_safety_tiers():
    no_ohko={"global_threat_complete":True,"no_known_guaranteed_ohko":"true"}
    all_preempted={"global_threat_complete":True,"no_known_guaranteed_ohko":"true","all_known_actions_preempted":"true"}
    incomplete={"global_threat_complete":False,"no_known_guaranteed_ohko":"true","all_known_actions_preempted":"true"}
    assert _tier(no_ohko)==("complete_set_no_guaranteed_ohko",4)
    assert _tier(all_preempted)==("complete_set_all_actions_preempted",5)
    assert _tier(incomplete)==("neutral_no_positive_threat_evidence",3)


def test_probability_selectability_and_base_rank_tie_break_are_outside_threat_tier():
    left={"known_executed_possible_ohko_threat_exists":True,"ko_by_1":{"numerator":9,"denominator":10}}
    right={"known_executed_possible_ohko_threat_exists":True,"ko_by_1":{"numerator":1,"denominator":10}}
    assert _tier(left)==_tier(right)==("executed_possible_ohko",2)
    assert "selectable" not in left and "provider_rank" not in left
