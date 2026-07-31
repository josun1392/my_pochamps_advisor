from llm.advisor_candidate_contract import build_recommendation_presentation_model, complete_recommendation_cycle
from scripts.run_sanitized_multi_move_mechanics_smoke import GROUNDING_FIXTURES, _prepared


def _provider_choice(prepared):
    rows = prepared["recommendation_request"]["candidate_comparisons"]
    winner = next(row for row in rows if row["mechanics_comparison"]["rank"] == 1)
    return {
        "recommendation_status": "resolved",
        "selected_candidate_id": winner["slot_index"],
        "explanation_code": "clear_ranked_winner",
    }


def test_multi_provider_choice_resolves_only_its_request_start_candidate_evidence():
    prepared = _prepared(GROUNDING_FIXTURES[0])
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=_provider_choice(prepared))
    result = completed["recommendation_result"]
    assert completed["status"] == result["status"] == "resolved"
    assert result["selected_candidate_id"] == result["recommended_slot_index"] == 1
    assert result["selected_action"] == {"slot_index": 1, "move": "slam"}
    assert result["explanation_code"] == "clear_ranked_winner"
    selected = result["selected_candidate_evidence"]
    source = prepared["recommendation_request"]["candidate_comparisons"][1]
    assert selected["mechanics_result"] == source["mechanics_result"]
    assert selected["action_order"] == source["action_order"]
    assert selected["comparison_facts"] == source["comparison_facts"]
    assert selected["comparison_facts"]["candidate_id"] == result["selected_action"]


def test_invalid_provider_choice_does_not_reuse_a_previous_or_other_candidate_result():
    prepared = _prepared(GROUNDING_FIXTURES[0])
    invalid = _provider_choice(prepared)
    invalid["selected_candidate_id"] = 0
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=invalid)
    assert completed["status"] == "response_validation_failed"
    assert completed["recommendation_result"] is None
    assert completed["errors"] == ["multi_provider_binding_invalid"]


def test_presentation_exposes_only_the_validated_selected_candidate_summary():
    prepared = _prepared(GROUNDING_FIXTURES[0])
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=_provider_choice(prepared))
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    selected = presentation["selected_candidate"]
    assert selected["selected_action"] == {"slot_index": 1, "move": "slam"}
    assert selected["evidence"]["comparison_facts"]["candidate_id"] == selected["selected_action"]
    assert "raw_response" not in selected
