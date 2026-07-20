PRESENTATION_KEYS = {
    "status",
    "recommended_move",
    "recommended_slot_index",
    "primary_reasons",
    "risks",
    "alternatives",
    "candidate_summaries",
    "errors",
}


def test_future_presentation_model_accepts_only_validated_recommendation_fields():
    completed = {
        "status": "resolved",
        "recommendation_result": {
            "status": "resolved",
            "recommended_move": "flamethrower",
            "recommended_slot_index": 0,
            "primary_reasons": [],
            "risks": [],
            "alternatives": [],
            "errors": [],
        },
        "candidates": [{"slot_index": 0, "move": "flamethrower"}],
    }
    result = completed["recommendation_result"]
    presentation = {
        "status": result["status"], "recommended_move": result["recommended_move"],
        "recommended_slot_index": result["recommended_slot_index"],
        "primary_reasons": result["primary_reasons"], "risks": result["risks"],
        "alternatives": result["alternatives"], "candidate_summaries": completed["candidates"],
        "errors": result["errors"],
    }
    assert set(presentation) == PRESENTATION_KEYS
    assert presentation["status"] == "resolved"


def test_presentation_contract_excludes_unvalidated_or_provider_owned_content():
    forbidden = {
        "raw_response", "raw_prompt", "provider", "repository", "ui_object",
        "api_key", "authorization", "network_config", "traceback", "token_usage",
    }
    assert not (PRESENTATION_KEYS & forbidden)
    assert "recommendation_result" not in PRESENTATION_KEYS
