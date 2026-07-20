from llm.advisor_candidate_contract import build_recommendation_request


def _candidate(slot, move, status, availability, **extra):
    return {"slot_index": slot, "move": move, "status": status, "availability": availability,
            "damage": {"status": "not_applicable"} if status == "partial" else {"status": "unavailable"},
            "self_effects": [], "dynamic_move": None, "warnings": [], "unavailable_reasons": [], **extra}


def _request(candidates):
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})


def test_resolved_partial_and_unavailable_candidates_have_required_eligibility():
    request = _request([
        _candidate(0, "resolved", "resolved", "usable"),
        _candidate(1, "partial", "partial", "partially_evaluable"),
        _candidate(2, "missing", "unavailable", "unavailable"),
    ])
    assert [row["eligibility"] for row in request["candidate_comparisons"]] == ["eligible", "eligible_with_warnings", "not_selectable"]


def test_non_damaging_partial_candidate_remains_selectable_with_warnings():
    request = _request([_candidate(0, "protect", "partial", "partially_evaluable", warnings=["unsupported_non_damage_utility_ranking"])])
    assert request["readiness"]["status"] == "ready"
    assert request["selectable_candidate_exact_set"] == [{"slot_index": 0, "move": "protect"}]
