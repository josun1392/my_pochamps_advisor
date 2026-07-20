from llm.advisor_candidate_contract import build_recommendation_presentation_model


def _completed(status="resolved", result_status=None):
    selected = None if status != "resolved" else "tackle"
    slot = None if status != "resolved" else 0
    result_status = result_status or status
    return {"status": status, "candidates": [{"slot_index": 0, "move": "tackle"}, {"slot_index": 2, "move": "tackle"}], "recommendation_result": {"status": result_status, "recommended_move": selected, "recommended_slot_index": slot, "primary_reasons": [], "risks": [], "alternatives": [], "errors": []}, "errors": []}


def test_resolved_and_declined_completion_models_preserve_validated_fields_and_slot_order():
    resolved = build_recommendation_presentation_model(completed_cycle=_completed())
    insufficient = build_recommendation_presentation_model(completed_cycle=_completed("insufficient_context"))
    no_usable = build_recommendation_presentation_model(completed_cycle=_completed("no_usable_candidate"))
    assert resolved["status"] == "resolved" and resolved["recommended_slot_index"] == 0
    assert insufficient["status"] == "insufficient_context" and insufficient["recommended_move"] is None
    assert no_usable["status"] == "no_usable_candidate" and [row["slot_index"] for row in no_usable["candidate_summaries"]] == [0, 2]


def test_validation_failure_is_never_promoted_to_resolved():
    completed = {"status": "response_validation_failed", "candidates": [{"slot_index": 0, "move": "tackle"}], "recommendation_result": None, "errors": ["recommended_candidate_not_selectable"]}
    model = build_recommendation_presentation_model(completed_cycle=completed)
    assert model["status"] == "validation_failed" and model["recommended_move"] is None
    assert model["errors"] == ["recommended_candidate_not_selectable"]
