from llm.advisor_client import _normalized_structured_usage


def test_usage_metadata_is_allowlisted_and_partial_or_invalid_values_are_sanitized():
    usage = _normalized_structured_usage(usage_data={"promptTokenCount": 1, "candidatesTokenCount": -1}, model="m")
    assert set(usage) == {"input_tokens", "output_tokens", "cached_tokens", "model", "tool", "success", "failure_code"}
    assert usage["input_tokens"] == 1 and usage["output_tokens"] == 0 and usage["failure_code"] == "provider_usage_unavailable"


def test_usage_metadata_missing_is_safe_and_never_contains_provider_object():
    usage = _normalized_structured_usage(usage_data=None, model="m")
    assert usage["input_tokens"] == usage["output_tokens"] == usage["cached_tokens"] == 0
