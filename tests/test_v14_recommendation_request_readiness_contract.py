from llm.advisor_candidate_contract import build_recommendation_request


def _candidate(slot, status="partial", availability="partially_evaluable"):
    return {"slot_index": slot, "move": f"move-{slot}", "status": status, "availability": availability,
            "damage": {"status": "not_applicable"}, "self_effects": [], "dynamic_move": None,
            "warnings": [], "unavailable_reasons": []}


def _bundle(candidates):
    return {"battle_snapshot_summary": {"field": "rain"}, "candidates": candidates, "known_limitations": []}


def test_no_candidates_and_no_selectable_candidates_have_distinct_readiness():
    assert build_recommendation_request(evidence_bundle=_bundle([]))["readiness"]["status"] == "no_candidates"
    assert build_recommendation_request(evidence_bundle=_bundle([_candidate(0, "unavailable", "unavailable")]))["readiness"]["status"] == "no_selectable_candidates"


def test_partial_only_candidates_are_ready_and_invalid_evidence_is_not_ready():
    assert build_recommendation_request(evidence_bundle=_bundle([_candidate(0)]))["readiness"]["status"] == "ready"
    invalid = build_recommendation_request(evidence_bundle=_bundle([_candidate(0), _candidate(0)]))
    assert invalid["readiness"] == {"status": "invalid_evidence_bundle", "selectable_candidate_count": 0}
