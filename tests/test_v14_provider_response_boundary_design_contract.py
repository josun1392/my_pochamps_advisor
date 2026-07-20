ALLOWED_STATUSES = {"resolved", "insufficient_context", "no_usable_candidate"}


def test_structured_response_boundary_excludes_local_validation_status_and_freeform_text():
    response = {"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []}
    assert response["recommendation_status"] in ALLOWED_STATUSES
    assert "validation_failed" not in ALLOWED_STATUSES and not isinstance(response, str)


def test_raw_response_and_provider_objects_cannot_cross_future_ui_handoff():
    handoff = {"prepared_cycle": {}, "recommendation_result": {}, "provider_status": "sanitized", "errors": []}
    assert not ({"raw_response", "provider_object", "prompt", "authorization"} & set(handoff))
