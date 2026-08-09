from __future__ import annotations

import json

from llm.advisor_candidate_contract import (
    build_provider_recommendation_payload,
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
)
from llm.advisor_client import format_recommendation_presentation_text
from scripts.run_sanitized_multi_move_mechanics_smoke import (
    EXACT_KO_PROBABILITY_FIXTURES,
    FIXED_HIT_FIXTURES,
    PSYCHIC_TERRAIN_PRIORITY_BLOCK_FIXTURES,
    _prepared,
)


def _rank_one_response(prepared: dict[str, object]) -> dict[str, object]:
    request = prepared["recommendation_request"]
    winner = next(
        row for row in request["candidate_comparisons"]
        if row["mechanics_comparison"].get("rank") == 1
    )
    return {
        "recommendation_status": "resolved",
        "selected_candidate_id": winner["slot_index"],
        "explanation_code": "clear_ranked_winner",
    }


def test_formula_probability_closure_preserves_roll_authority_ko_layers_and_exact_fractions():
    prepared = _prepared(EXACT_KO_PROBABILITY_FIXTURES[0])
    formula, control = prepared["candidates"]
    mechanics = formula["mechanics_result"]
    rolls = mechanics["exact_damage_rolls"]
    probability = mechanics["ko_probability"]

    assert mechanics["damage_model"] == "single_hit_formula"
    assert len(rolls) == 16
    assert len(set(rolls)) < len(rolls)  # Final-damage duplicates remain probability multiplicity.
    assert min(rolls) == mechanics["damage_range"]["minimum"]
    assert max(rolls) == mechanics["damage_range"]["maximum"]
    assert mechanics["ko_interpretation"]["primary_ko_label"] == "possible_ohko"
    assert probability == {
        "ko_probability_supportability": "complete",
        "defender_hp_authority": "exact_current_hp",
        "damage_roll_distribution_basis": "server_owned_exact_damage_rolls",
        "probability_model": "independent_repeated_noncritical_damage_rolls",
        "ko_by_1": {"numerator": 3, "denominator": 4},
        "ko_by_2": {"numerator": 1, "denominator": 1},
        "ko_by_3": {"numerator": 1, "denominator": 1},
    }
    assert control["mechanics_result"].get("ko_probability") is None


def test_unknown_hp_keeps_formula_rolls_and_usability_but_withholds_ko_probability():
    prepared = _prepared(EXACT_KO_PROBABILITY_FIXTURES[1])
    formula, control = prepared["candidates"]
    mechanics = formula["mechanics_result"]

    assert formula["availability"] == "partially_evaluable"
    assert len(mechanics["exact_damage_rolls"]) == 16
    assert mechanics["ko_interpretation"] == {
        "ko_supportability": "insufficient_context",
        "missing_inputs": ["opponent.current_hp"],
    }
    assert mechanics["ko_probability"] == {
        "ko_probability_supportability": "insufficient_context",
        "missing_inputs": ["opponent.current_hp"],
    }
    assert control["mechanics_result"].get("ko_probability") is None


def test_formula_probability_stays_out_of_fixed_and_move_success_blocked_candidate_classes():
    fixed = _prepared(FIXED_HIT_FIXTURES[0])["candidates"][0]["mechanics_result"]
    blocked = _prepared(PSYCHIC_TERRAIN_PRIORITY_BLOCK_FIXTURES[0])["candidates"][0]

    assert fixed["damage_model"] == "fixed_hit_formula"
    assert "exact_damage_rolls" not in fixed
    assert "ko_probability" not in fixed
    assert blocked["availability"] == "unavailable"
    assert "exact_damage_rolls" not in blocked["mechanics_result"]
    assert "ko_probability" not in blocked["mechanics_result"]


def test_provider_and_selected_presentation_keep_probability_candidate_local():
    prepared = _prepared(EXACT_KO_PROBABILITY_FIXTURES[0])
    provider_payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    completed = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload=_rank_one_response(prepared),
    )
    selected = completed["recommendation_result"]["selected_candidate_evidence"]["mechanics_result"]
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    text = format_recommendation_presentation_text(presentation_model=presentation)

    assert "exact_damage_rolls" not in json.dumps(provider_payload, sort_keys=True)
    assert "ko_probability" not in json.dumps(provider_payload, sort_keys=True)
    assert "exact_damage_rolls" not in selected
    assert selected["ko_probability"]["ko_by_1"] == {"numerator": 3, "denominator": 4}
    assert all("ko_probability" not in row.get("mechanics_result", {}) for row in presentation["candidate_summaries"])
    assert "확률로" in text
