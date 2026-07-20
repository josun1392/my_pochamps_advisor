from llm.advisor_client import format_recommendation_presentation_text


def test_failure_formatting_is_friendly_and_does_not_expose_internal_input():
    for status in ("preparation_not_ready", "provider_unavailable", "provider_timeout", "provider_safety_blocked", "provider_response_malformed", "response_validation_failed"):
        text = format_recommendation_presentation_text(presentation_model={"status": status, "errors": ["raw_response=secret"]})
        assert "raw_response" not in text and "secret" not in text


def test_resolved_formatter_keeps_move_and_slot_paired_and_sections_ordered():
    text = format_recommendation_presentation_text(presentation_model={"status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": []})
    assert text.index("추천 기술") < text.index("슬롯") < text.index("주요 이유") < text.index("후보 요약")
