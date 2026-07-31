from copy import deepcopy

from llm.advisor_candidate_contract import (
    build_provider_recommendation_payload,
    build_recommendation_request,
    prepare_ui_recommendation_cycle,
    rank_direct_mechanics_candidates,
)
from llm.advisor_turn_snapshot import BASE_STAT_KEYS


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _candidate(slot, move, *, mechanics, status="resolved", availability="usable"):
    return {
        "slot_index": slot,
        "move": move,
        "status": status,
        "availability": availability,
        "self_effects": [],
        "dynamic_move": None,
        "warnings": [],
        "unavailable_reasons": [],
        "mechanics_result": mechanics,
    }


def _known(*, minimum, maximum, minimum_percent=None, maximum_percent=None, probability=0.0, effectiveness=1.0):
    return {
        "status": "known",
        "move": "bounded",
        "type_effectiveness": effectiveness,
        "damage_range": {"minimum": minimum, "maximum": maximum},
        "damage_percent_range": {"minimum": minimum if minimum_percent is None else minimum_percent, "maximum": maximum if maximum_percent is None else maximum_percent},
        "ko_result": {"status": "resolved", "single_hit_probability": probability},
        "missing_inputs": [],
        "unsupported_reason": None,
        "mechanics_source": "native_q12_direct_damage",
        "generation": "gen9",
    }


def _insufficient():
    return {
        "status": "insufficient_context",
        "move": None,
        "type_effectiveness": None,
        "damage_range": None,
        "damage_percent_range": None,
        "ko_result": None,
        "missing_inputs": ["defender.item"],
        "unsupported_reason": None,
        "mechanics_source": "native_q12_direct_damage",
        "generation": None,
    }


def _unsupported():
    return {
        "status": "unsupported_mechanic",
        "move": None,
        "type_effectiveness": None,
        "damage_range": None,
        "damage_percent_range": None,
        "ko_result": None,
        "missing_inputs": [],
        "unsupported_reason": "dynamic_base_power",
        "mechanics_source": "native_q12_direct_damage",
        "generation": None,
    }


def _provenance(side, slot, pokemon):
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "multi", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}


def _battle(*, incomplete=False):
    entries = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        entries.extend(
            {"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)}
            for index, key in enumerate(BASE_STAT_KEYS)
        )
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "status": absent, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100}
    if incomplete:
        side = deepcopy(side)
        side["item"] = {"status": "unknown"}
    return {
        "current_state_session_id": "multi",
        "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}},
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}, {"slot_index": 1, "move_id": "slam"}]},
        "final_stat_context": {"current_final_stats": entries},
        "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {**_provenance("self", 0, "pikachu"), "source": "user_confirmed_current_level"}}]},
        "direct_mechanics_context": {"generation": "gen9", "attacker": deepcopy(side), "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}},
    }


def test_known_moves_use_guaranteed_ko_then_damage_floor_and_stable_slot_order():
    candidates = [
        _candidate(2, "high-maximum", mechanics=_known(minimum=40, maximum=100, probability=0)),
        _candidate(1, "high-minimum", mechanics=_known(minimum=50, maximum=60, probability=0)),
        _candidate(3, "guaranteed", mechanics=_known(minimum=1, maximum=2, probability=1)),
        _candidate(0, "same-as-high-minimum", mechanics=_known(minimum=50, maximum=60, probability=0)),
    ]
    before = deepcopy(candidates)
    ranked = rank_direct_mechanics_candidates(candidates=candidates)
    assert [move for (_slot, move), value in sorted(ranked.items(), key=lambda item: item[1]["rank"])] == ["guaranteed", "same-as-high-minimum", "high-minimum", "high-maximum"]
    assert ranked[(0, "same-as-high-minimum")]["rank"] == 2
    assert ranked[(1, "high-minimum")]["rank"] == 3
    assert candidates == before


def test_immunity_is_rankable_but_loses_to_an_effective_known_action():
    ranked = rank_direct_mechanics_candidates(candidates=[
        _candidate(0, "immune", mechanics=_known(minimum=0, maximum=0, effectiveness=0)),
        _candidate(1, "effective", mechanics=_known(minimum=1, maximum=2, effectiveness=1)),
    ])
    assert ranked[(1, "effective")]["rank"] == 1
    assert ranked[(0, "immune")] == {"comparison_status": "rankable", "rank": 2, "comparison_reason": "deterministic_known_mechanics"}


def test_provider_rows_add_candidate_local_native_comparison_facts_without_reranking():
    candidates = [
        _candidate(0, "immune", mechanics=_known(minimum=0, maximum=0, effectiveness=0)),
        _candidate(1, "ko", mechanics=_known(minimum=90, maximum=120, probability=1)),
        _candidate(2, "partial", mechanics=_insufficient(), status="partial", availability="partially_evaluable"),
        _candidate(3, "unsupported", mechanics=_unsupported(), status="partial", availability="partially_evaluable"),
    ]
    candidates[1]["action_order"] = {"status": "acts_first"}
    candidates[0]["action_order"] = {"status": "speed_tie"}
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})
    rows = request["candidate_comparisons"]
    assert [row["mechanics_comparison"]["rank"] for row in rows] == [2, 1, None, None]
    assert rows[0]["comparison_facts"] == {
        "candidate_id": {"slot_index": 0, "move": "immune"}, "mechanics_status": "known",
        "action_order_status": "speed_tie", "comparison_tags": ["immune", "speed_tie"],
        "evidence_refs": ["mechanics_result", "action_order"],
    }
    assert set(rows[1]["comparison_facts"]["comparison_tags"]) == {"guaranteed_ohko", "higher_native_damage_range", "acts_first_if_known"}
    assert rows[2]["comparison_facts"]["comparison_tags"] == ["insufficient_mechanics_context"]
    assert rows[3]["comparison_facts"]["comparison_tags"] == ["unsupported_mechanic"]
    assert all(row["comparison_facts"]["candidate_id"] == {"slot_index": row["slot_index"], "move": row["move"]} for row in rows)


def test_insufficient_unsupported_and_unavailable_never_receive_ranks_and_only_known_is_explicit():
    candidates = [
        _candidate(0, "known", mechanics=_known(minimum=1, maximum=2)),
        _candidate(1, "incomplete", mechanics=_insufficient(), status="partial", availability="partially_evaluable"),
        _candidate(2, "unsupported", mechanics=_unsupported(), status="partial", availability="partially_evaluable"),
        _candidate(3, "unavailable", mechanics=_known(minimum=9, maximum=10), status="unavailable", availability="unavailable"),
    ]
    ranked = rank_direct_mechanics_candidates(candidates=candidates)
    assert ranked[(0, "known")] == {"comparison_status": "rankable", "rank": 1, "comparison_reason": "only_rankable_candidate"}
    assert ranked[(1, "incomplete")]["comparison_status"] == "insufficient_context"
    assert ranked[(2, "unsupported")]["comparison_status"] == "unsupported_mechanic"
    assert ranked[(3, "unavailable")]["comparison_status"] == "unavailable"
    assert all(value["rank"] is None for key, value in ranked.items() if key != (0, "known"))


def test_no_rankable_candidates_preserve_incomplete_and_unsupported_categories():
    ranked = rank_direct_mechanics_candidates(candidates=[
        _candidate(0, "incomplete", mechanics=_insufficient(), status="partial", availability="partially_evaluable"),
        _candidate(1, "unsupported", mechanics=_unsupported(), status="partial", availability="partially_evaluable"),
    ])
    assert {value["comparison_status"] for value in ranked.values()} == {"insufficient_context", "unsupported_mechanic"}
    assert all(value["rank"] is None for value in ranked.values())


def test_multi_slot_preparation_carries_independent_results_and_ranks_into_provider_payload():
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}, {"move_id": "slam"}],
        battle_input=_battle(),
        move_repository={
            "tackle": {"category": "physical", "power": 40, "type": "normal"},
            "slam": {"category": "physical", "power": 100, "type": "normal"},
        },
        species_repository=_Species(),
    )
    assert prepared["status"] == "ready"
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    assert [row["mechanics_result"]["move"] for row in rows] == ["tackle", "slam"]
    assert [row["mechanics_comparison"]["rank"] for row in rows] == [2, 1]
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    assert [row["mechanics_comparison"]["rank"] for row in payload["candidate_comparisons"]] == [2, 1]
    assert all("q12_damage" not in row and "damage_rolls" not in row for row in payload["candidate_comparisons"])


def test_multiple_incomplete_moves_remain_unranked_without_default_values():
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}, {"move_id": "slam"}],
        battle_input=_battle(incomplete=True),
        move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}, "slam": {"category": "physical", "power": 100, "type": "normal"}},
        species_repository=_Species(),
    )
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    assert all(row["mechanics_comparison"]["comparison_status"] == "insufficient_context" for row in rows)
    assert all(row["mechanics_comparison"]["rank"] is None for row in rows)
    assert all(row["mechanics_result"]["damage_range"] is None for row in rows)


def test_request_validation_rejects_provider_ranking_mutation():
    candidates = [_candidate(0, "first", mechanics=_known(minimum=1, maximum=2)), _candidate(1, "second", mechanics=_known(minimum=2, maximum=3))]
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})
    request["candidate_comparisons"][0]["mechanics_comparison"]["rank"] = 1
    from llm.advisor_candidate_contract import validate_recommendation_selection
    import pytest
    with pytest.raises(ValueError):
        validate_recommendation_selection(request=request, recommended_move="second", recommended_slot_index=1)


def test_request_validation_rejects_cross_candidate_comparison_fact_mutation():
    candidates = [_candidate(0, "first", mechanics=_known(minimum=1, maximum=2)), _candidate(1, "second", mechanics=_known(minimum=2, maximum=3))]
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})
    request["candidate_comparisons"][0]["comparison_facts"]["candidate_id"] = {"slot_index": 1, "move": "second"}
    from llm.advisor_candidate_contract import validate_recommendation_selection
    import pytest
    with pytest.raises(ValueError):
        validate_recommendation_selection(request=request, recommended_move="second", recommended_slot_index=1)
