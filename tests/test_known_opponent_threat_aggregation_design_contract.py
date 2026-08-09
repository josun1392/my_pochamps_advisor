"""Design-only contract: no production threat aggregation is introduced here."""


def _summary(pairs, *, state, complete, unknown_slots):
    executable = [pair for pair in pairs if pair["opponent_move_success"] == "allowed" and pair["opponent_preemption"] != "preempted"]
    guaranteed = [pair for pair in executable if pair["opponent_ohko"] == "guaranteed"]
    possible = [pair for pair in executable if pair["opponent_ohko"] == "possible"]
    evaluated = all(pair["supportability"] == "complete" for pair in pairs)
    exhaustive = complete and evaluated and bool(pairs)
    return {"opponent_known_move_state": state, "known_pair_count": len(pairs), "unknown_slots_remaining": unknown_slots, "candidate_set_complete": complete, "known_guaranteed_ohko_threat_exists": bool(guaranteed), "known_possible_ohko_threat_exists": bool(possible), "known_threat_evaluation_complete": exhaustive, "global_threat_complete": exhaustive, "no_known_guaranteed_ohko": "true" if exhaustive and not guaranteed else "false" if guaranteed else "unresolved", "all_known_actions_preempted": "true" if pairs and all(pair["opponent_preemption"] == "preempted" for pair in pairs) else "false" if any(pair["opponent_preemption"] != "preempted" for pair in pairs) else "unresolved"}


def _pair(ohko="no", *, preempted=False, supportability="complete"):
    return {"opponent_move_success": "allowed", "opponent_preemption": "preempted" if preempted else "executable", "opponent_ohko": ohko, "supportability": supportability}


def test_unknown_and_partial_known_sets_never_produce_global_safety_or_negative_universal_claims():
    unknown = _summary([], state="unknown", complete=False, unknown_slots=4)
    partial = _summary([_pair(), _pair()], state="partially_known", complete=False, unknown_slots=2)
    assert unknown["known_pair_count"] == 0 and unknown["no_known_guaranteed_ohko"] == "unresolved"
    assert partial["known_guaranteed_ohko_threat_exists"] is False
    assert partial["global_threat_complete"] is False and partial["no_known_guaranteed_ohko"] == "unresolved"


def test_positive_known_executed_ohko_threat_survives_partial_or_incomplete_evidence():
    result = _summary([_pair("guaranteed"), _pair(supportability="unsupported_mechanic")], state="partially_known", complete=False, unknown_slots=2)
    assert result["known_guaranteed_ohko_threat_exists"] is True
    assert result["known_threat_evaluation_complete"] is False


def test_preempted_opponent_ko_is_raw_capability_not_executed_immediate_threat():
    result = _summary([_pair("guaranteed", preempted=True)], state="complete", complete=True, unknown_slots=0)
    assert result["known_guaranteed_ohko_threat_exists"] is False
    assert result["all_known_actions_preempted"] == "true"


def test_complete_mechanically_evaluated_set_can_resolve_negative_universal_but_probability_stays_pair_local():
    result = _summary([_pair(), _pair(), _pair(), _pair()], state="complete", complete=True, unknown_slots=0)
    pair_probability = {"ko_by_1": {"numerator": 3, "denominator": 4}}
    assert result["known_threat_evaluation_complete"] is True
    assert result["no_known_guaranteed_ohko"] == "true"
    assert "aggregate_probability" not in result and pair_probability["ko_by_1"] == {"numerator": 3, "denominator": 4}
