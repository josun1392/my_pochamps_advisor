import inspect
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_both_actions_are_disabled_while_any_advice_request_is_running():
    source = inspect.getsource(LLMAdvicePanel.set_running)
    assert "request_button.setDisabled(is_running)" in source
    assert "structured_request_button.setDisabled(is_running)" in source


def test_actions_start_only_their_own_workers():
    assert "LLMAdviceWorker" in inspect.getsource(MainWindow._start_llm_advice)
    assert "StructuredRecommendationWorker" not in inspect.getsource(MainWindow._start_llm_advice)
    assert "StructuredRecommendationWorker" in inspect.getsource(MainWindow._start_structured_recommendation)
