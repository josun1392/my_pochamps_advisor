import pytest

from llm.advisor_candidate_contract import build_recommendation_request, validate_recommendation_selection


def _candidate(slot, move, status="resolved", availability="usable"):
    return {"slot_index": slot, "move": move, "status": status, "availability": availability,
            "damage": {"status": "resolved", "minimum": 1, "maximum": 2}, "hit_chance": {"status": "resolved"},
            "move_order": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}


def _request(candidates):
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})


def test_exact_sets_preserve_duplicate_move_slots_and_comparison_fields():
    request = _request([_candidate(0, "flamethrower"), _candidate(2, "flamethrower"), _candidate(3, "missing", "unavailable", "unavailable")])
    assert request["candidate_exact_set"] == [{"slot_index": 0, "move": "flamethrower"}, {"slot_index": 2, "move": "flamethrower"}, {"slot_index": 3, "move": "missing"}]
    assert request["selectable_candidate_exact_set"] == request["candidate_exact_set"][:2]
    assert {"damage", "hit_chance", "move_order", "dynamic_move", "self_effects", "warnings", "unavailable_reasons"} <= set(request["candidate_comparisons"][0])


def test_selection_requires_the_exact_selectable_move_and_slot_pair():
    request = _request([_candidate(0, "flamethrower"), _candidate(1, "missing", "unavailable", "unavailable")])
    assert validate_recommendation_selection(request=request, recommended_move="flamethrower", recommended_slot_index=0) == {"move": "flamethrower", "slot_index": 0}
    for move, slot in (("flamethrower", 1), ("unknown", 0), ("missing", 1)):
        with pytest.raises(ValueError):
            validate_recommendation_selection(request=request, recommended_move=move, recommended_slot_index=slot)
    non_ready = _request([])
    with pytest.raises(ValueError):
        validate_recommendation_selection(request=non_ready, recommended_move="flamethrower", recommended_slot_index=0)


def test_duplicate_slots_and_comparison_exact_set_drift_are_rejected():
    assert _request([_candidate(0, "a"), _candidate(0, "b")])["readiness"]["status"] == "invalid_evidence_bundle"
    request = _request([_candidate(0, "a")])
    request["candidate_comparisons"][0]["move"] = "mutated"
    with pytest.raises(ValueError):
        validate_recommendation_selection(request=request, recommended_move="a", recommended_slot_index=0)
