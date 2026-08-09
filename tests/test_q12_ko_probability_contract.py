from __future__ import annotations

import json

from llm.advisor_candidate_contract import (
    build_provider_recommendation_payload,
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
)
from llm.advisor_client import _format_exact_ko_probability, format_recommendation_presentation_text
from llm.q12_ko_probability import evaluate_exact_q12_ko_probability
from scripts.run_sanitized_multi_move_mechanics_smoke import KO_INTERPRETATION_FIXTURES, _prepared


def _hp(current: int) -> dict[str, object]:
    return {"current_hp": [{"side": "opponent", "current_hp": current, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"}]}


def _mechanics(rolls: tuple[int, ...]) -> dict[str, object]:
    return {"status": "known", "damage_model": "single_hit_formula", "damage_range": {"minimum": min(rolls), "maximum": max(rolls)}, "exact_damage_rolls": rolls}


def test_exact_probability_uses_duplicate_roll_multiplicity_and_cumulative_convolution():
    result = evaluate_exact_q12_ko_probability(
        mechanics_result=_mechanics((10, 10, 20, 20)), current_hp_context=_hp(20), defender_side="opponent",
        ko_interpretation={"ko_supportability": "complete", "ohko_result": "possible", "two_hko_result": "guaranteed", "three_hko_result": "guaranteed"},
    )

    assert result == {
        "ko_probability_supportability": "complete",
        "defender_hp_authority": "exact_current_hp",
        "damage_roll_distribution_basis": "server_owned_exact_damage_rolls",
        "probability_model": "independent_repeated_noncritical_damage_rolls",
        "ko_by_1": {"numerator": 1, "denominator": 2},
        "ko_by_2": {"numerator": 1, "denominator": 1},
        "ko_by_3": {"numerator": 1, "denominator": 1},
    }


def test_exact_probability_keeps_possible_ohko_precedence_consistent_with_guaranteed_two_hko():
    result = evaluate_exact_q12_ko_probability(
        mechanics_result=_mechanics((10, 20)), current_hp_context=_hp(20), defender_side="opponent",
        ko_interpretation={"ko_supportability": "complete", "ohko_result": "possible", "two_hko_result": "guaranteed", "three_hko_result": "guaranteed", "primary_ko_label": "possible_ohko"},
    )

    assert result is not None
    assert result["ko_by_1"] == {"numerator": 1, "denominator": 2}
    assert result["ko_by_2"] == result["ko_by_3"] == {"numerator": 1, "denominator": 1}


def test_exact_probability_handles_no_ko_and_shared_hp_omission_or_fainted_boundaries():
    mechanics = _mechanics((10, 20))
    no_ko = evaluate_exact_q12_ko_probability(
        mechanics_result=mechanics, current_hp_context=_hp(100), defender_side="opponent",
        ko_interpretation={"ko_supportability": "complete", "ohko_result": "no", "two_hko_result": "no", "three_hko_result": "no"},
    )
    assert no_ko is not None
    assert no_ko["ko_by_1"] == no_ko["ko_by_2"] == no_ko["ko_by_3"] == {"numerator": 0, "denominator": 1}
    assert evaluate_exact_q12_ko_probability(mechanics_result=mechanics, current_hp_context=None, defender_side="opponent", ko_interpretation=None) is None
    assert evaluate_exact_q12_ko_probability(mechanics_result=mechanics, current_hp_context=_hp(0), defender_side="opponent", ko_interpretation=None) == {"ko_probability_supportability": "not_applicable", "reason": "target_already_fainted"}


def test_probability_rejects_mismatched_roll_authority_and_formats_only_exact_extremes_as_zero_or_one_hundred():
    invalid = {**_mechanics((10, 20)), "damage_range": {"minimum": 10, "maximum": 21}}
    assert evaluate_exact_q12_ko_probability(mechanics_result=invalid, current_hp_context=_hp(20), defender_side="opponent", ko_interpretation=None) == {"ko_probability_supportability": "unsupported_mechanic", "reason": "exact_damage_rolls"}
    assert _format_exact_ko_probability({"numerator": 0, "denominator": 16}) == "0%"
    assert _format_exact_ko_probability({"numerator": 16, "denominator": 16}) == "100%"
    assert _format_exact_ko_probability({"numerator": 4095, "denominator": 4096}) == ">99.9%"


def test_unknown_hp_is_probability_insufficient_without_formula_candidate_usability_change():
    prepared = _prepared(KO_INTERPRETATION_FIXTURES[1])
    formula, control = prepared["candidates"]

    assert formula["availability"] == "partially_evaluable"
    assert formula["mechanics_result"]["ko_probability"] == {
        "ko_probability_supportability": "insufficient_context", "missing_inputs": ["opponent.current_hp"]
    }
    assert "ko_probability" not in control["mechanics_result"]


def test_provider_excludes_probability_but_selected_presentation_uses_only_selected_server_evidence():
    prepared = _prepared(KO_INTERPRETATION_FIXTURES[0])
    request = prepared["recommendation_request"]
    provider_payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    winner = next(row for row in request["candidate_comparisons"] if row["mechanics_comparison"].get("rank") == 1)
    completed = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload={"recommendation_status": "resolved", "selected_candidate_id": winner["slot_index"], "explanation_code": "clear_ranked_winner"},
    )
    selected = completed["recommendation_result"]["selected_candidate_evidence"]["mechanics_result"]
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    text = format_recommendation_presentation_text(presentation_model=presentation)

    assert "ko_probability" not in json.dumps(provider_payload, sort_keys=True)
    assert all("ko_probability" not in candidate.get("mechanics_result", {}) for candidate in presentation["candidate_summaries"])
    assert selected["ko_probability"]["ko_probability_supportability"] == "complete"
    assert "피해 난수 기준" in text
