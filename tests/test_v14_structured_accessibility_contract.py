import inspect
from llm.advisor_client import format_recommendation_presentation_text
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_resolved_formatter_gives_empty_optional_sections_explicit_content():
    text = format_recommendation_presentation_text(presentation_model={"status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": []})
    assert "추천 기술" in text and "슬롯" in text
    assert "주요 이유: 없음" in text and "위험 요소: 없음" in text and "대안: 없음" in text


def test_panel_output_remains_selectable_and_buttons_have_accessibility_metadata():
    source = inspect.getsource(LLMAdvicePanel)
    assert "self.output_edit.setReadOnly(True)" in source and "setAccessibleName" in source
