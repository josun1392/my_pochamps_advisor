import inspect

from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_panel_has_separate_structured_action_and_legacy_action():
    source = inspect.getsource(LLMAdvicePanel)
    assert "advice_requested" in source and "structured_advice_requested" in source
    assert "구조화 추천 받기" in source


def test_main_window_keeps_legacy_and_structured_starts_separate():
    legacy = inspect.getsource(MainWindow._start_llm_advice)
    structured = inspect.getsource(MainWindow._start_structured_recommendation)
    assert "LLMAdviceWorker" in legacy and "StructuredRecommendationWorker" not in legacy
    assert "StructuredRecommendationWorker" in structured and "run_ui_selected_advice" not in structured
