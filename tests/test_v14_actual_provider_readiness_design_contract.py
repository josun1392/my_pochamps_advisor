import inspect

from scripts.spike_advisor import call_gemini


STRUCTURED_CALL_POLICY = {
    "payload_fields": ("request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails"),
    "maximum_calls": 1,
    "retry": False,
    "fallback": False,
    "raw_response_retained": False,
}


def test_current_freeform_client_cannot_be_reused_as_structured_boundary_without_adapter():
    source = inspect.getsource(call_gemini)
    assert "prompt: str" in source and '"parts": [{"text": prompt}]' in source
    assert "response_schema" not in source and "response_mime_type" not in source
    assert "usageMetadata" in source and "finishReason" not in source


def test_future_structured_provider_policy_is_one_call_and_seven_field_only():
    assert len(STRUCTURED_CALL_POLICY["payload_fields"]) == 7
    assert STRUCTURED_CALL_POLICY["maximum_calls"] == 1
    assert not STRUCTURED_CALL_POLICY["retry"] and not STRUCTURED_CALL_POLICY["fallback"]
    assert not STRUCTURED_CALL_POLICY["raw_response_retained"]
