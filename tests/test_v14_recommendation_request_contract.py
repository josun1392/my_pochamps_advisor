import pytest

from llm.advisor_candidate_contract import build_recommendation_request, validate_recommendation_selection


def _candidate(slot, move, status="partial", availability="partially_evaluable", dynamic=None):
    return {"slot_index": slot, "move": move, "status": status, "availability": availability,
            "damage": {"status": "not_applicable"}, "dynamic_move": dynamic, "self_effects": [], "warnings": [], "unavailable_reasons": []}


def _request(candidates):
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})


@pytest.mark.parametrize(("family", "move"), [
    ("current_hp_based_power", "eruption"), ("speed_based_power", "electro-ball"), ("weight_based_power", "heavy-slam"),
    ("stat_stage_based_power", "stored-power"), ("target_hp_based_power", "crush-grip"), ("environment_based_move", "weather-ball"),
    ("binary_condition_power", "facade"), ("turn_event_power", "avalanche"), ("battle_counter_power", "rage-fist"), ("consecutive_use_power", "fury-cutter"),
])
def test_all_dynamic_family_candidate_summaries_are_request_compatible(family, move):
    dynamic = {"family": family, "status": "resolved", "effective_power": 100, "effective_type": "water" if family == "environment_based_move" else None}
    request = _request([_candidate(0, move, dynamic=dynamic)])
    assert request["readiness"]["status"] == "ready"
    assert request["candidate_comparisons"][0]["dynamic_move"] == dynamic


def test_unavailable_candidates_remain_full_exact_set_only():
    request = _request([_candidate(0, "usable"), _candidate(1, "missing", "unavailable", "unavailable")])
    assert request["candidate_exact_set"] == [{"slot_index": 0, "move": "usable"}, {"slot_index": 1, "move": "missing"}]
    assert request["selectable_candidate_exact_set"] == [{"slot_index": 0, "move": "usable"}]


def test_request_integrity_rejects_exact_set_and_order_mutations():
    request = _request([_candidate(0, "a"), _candidate(1, "b")])
    mutations = [
        lambda value: value["candidate_comparisons"].pop(),
        lambda value: value["candidate_exact_set"].pop(),
        lambda value: value["selectable_candidate_exact_set"].append({"slot_index": 3, "move": "outside"}),
        lambda value: value["selectable_candidate_exact_set"].append({"slot_index": 0, "move": "a"}),
        lambda value: value["candidate_exact_set"].reverse(),
        lambda value: value["candidate_comparisons"][0].update(move="mutated"),
    ]
    for mutate in mutations:
        altered = __import__("copy").deepcopy(request); mutate(altered)
        with pytest.raises(ValueError):
            validate_recommendation_selection(request=altered, recommended_move="a", recommended_slot_index=0)


def test_request_integrity_rejects_an_unavailable_candidate_in_selectable_set():
    request = _request([_candidate(0, "usable"), _candidate(1, "missing", "unavailable", "unavailable")])
    request["selectable_candidate_exact_set"].append({"slot_index": 1, "move": "missing"})
    with pytest.raises(ValueError):
        validate_recommendation_selection(request=request, recommended_move="usable", recommended_slot_index=0)
