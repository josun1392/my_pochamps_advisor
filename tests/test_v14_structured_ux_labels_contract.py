from PySide6.QtWidgets import QApplication

from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_buttons_have_distinct_korean_labels_tooltips_and_accessible_names():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()

    assert panel.request_button.text() == "선택 기술 LLM 조언"
    assert panel.structured_request_button.text() == "구조화 LLM 추천"
    assert "자유 형식 조언" in panel.request_button.toolTip()
    assert "후보 기술 전체" in panel.structured_request_button.toolTip()
    assert panel.request_button.accessibleName() == "선택 기술 LLM 조언"
    assert panel.structured_request_button.accessibleName() == "구조화 LLM 추천"
