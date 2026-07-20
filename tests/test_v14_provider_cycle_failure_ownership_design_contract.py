import inspect

from llm.advisor_client import run_ui_selected_advice


FAILURE_OWNERS = {
    "preparation_not_ready": ("prepared_cycle", False, False),
    "provider_failure": ("provider_adapter", True, False),
    "response_validation_failure": ("complete_recommendation_cycle", True, False),
}


def test_failure_ownership_preserves_evidence_and_blocks_unsafe_display():
    for owner, preserves_evidence, may_display_recommendation in FAILURE_OWNERS.values():
        assert owner
        assert may_display_recommendation is False
        if owner != "prepared_cycle":
            assert preserves_evidence is True


def test_provider_or_response_failure_never_carries_raw_payload_into_handoff():
    provider_failure = {
        "status": "provider_unavailable", "prepared_cycle": {"evidence_bundle": {"candidates": []}},
        "response_payload": None, "errors": ["provider_unavailable"],
    }
    semantic_failure = {
        "status": "response_validation_failed", "recommendation_result": None,
        "errors": ["recommended_candidate_not_selectable"],
    }
    assert provider_failure["prepared_cycle"]["evidence_bundle"] == {"candidates": []}
    assert provider_failure["response_payload"] is None
    assert semantic_failure["recommendation_result"] is None
    assert "raw_response" not in provider_failure | semantic_failure


def test_legacy_selected_move_flow_remains_separate_from_future_cycle():
    source = inspect.getsource(run_ui_selected_advice)
    assert "run_offline_recommendation_provider_adapter" not in source
    assert "complete_recommendation_cycle" not in source
