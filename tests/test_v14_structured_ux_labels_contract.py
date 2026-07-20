import inspect
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_buttons_have_distinct_korean_labels_tooltips_and_accessible_names():
    source = inspect.getsource(LLMAdvicePanel)
    assert "기존 선택 기술 조언" in source and "구조화 추천 받기" in source
    assert "자유 형식 조언" in source and "후보 기술 전체" in source
    assert "setAccessibleName" in source
