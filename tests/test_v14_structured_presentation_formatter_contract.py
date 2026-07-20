from llm.advisor_client import format_recommendation_presentation_text


def test_formatter_renders_validated_resolved_sections_only():
    text = format_recommendation_presentation_text(presentation_model={"status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": []})
    assert all(label in text for label in ("추천 기술", "슬롯", "주요 이유", "위험 요소", "대안", "후보 요약"))


def test_formatter_never_exposes_failure_details_or_fabricates_move():
    text = format_recommendation_presentation_text(presentation_model={"status": "provider_timeout", "errors": ["raw"]})
    assert text == "제공자 호출에 실패했습니다." and "raw" not in text
