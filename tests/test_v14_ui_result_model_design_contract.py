UI_RESULT_FIELDS = ("recommended_move", "recommended_slot_index", "primary_reasons", "risks", "alternatives", "errors")


def test_future_ui_result_model_is_structured_and_never_carries_raw_provider_text():
    model = {"recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "errors": []}
    assert tuple(model) == UI_RESULT_FIELDS
    assert not ({"raw_response", "provider_client", "token_log", "network_configuration"} & set(model))


def test_ui_adapter_is_a_future_layer_not_a_dependency_of_pure_results():
    pure_result = {"status": "resolved", "recommendation_result": {"recommended_move": "move"}, "errors": []}
    assert "widget" not in pure_result and "panel" not in pure_result and "display_text" not in pure_result
