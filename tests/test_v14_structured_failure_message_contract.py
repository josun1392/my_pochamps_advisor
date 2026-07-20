from llm.advisor_client import format_recommendation_presentation_text


def test_all_structured_failure_statuses_are_friendly_and_sanitized():
    statuses = ("preparation_not_ready", "provider_unavailable", "provider_timeout", "provider_safety_blocked", "provider_response_missing", "provider_response_malformed", "provider_structured_decode_failed", "provider_response_validation_failed", "response_validation_failed", "insufficient_context", "no_usable_candidate")
    for status in statuses:
        text = format_recommendation_presentation_text(presentation_model={"status": status, "errors": ["raw_response=secret"]})
        assert text and "raw_response" not in text and "secret" not in text
