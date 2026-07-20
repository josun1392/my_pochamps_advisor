import inspect

from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_structured_button_is_disabled_during_run_and_restored_on_both_paths():
    panel = inspect.getsource(LLMAdvicePanel.set_running)
    start = inspect.getsource(MainWindow._start_structured_recommendation)
    success = inspect.getsource(MainWindow._on_structured_recommendation_finished)
    failure = inspect.getsource(MainWindow._on_structured_recommendation_failed)
    assert "structured_request_button.setDisabled(is_running)" in panel
    assert "structured_request_button.setDisabled(True)" in start
    assert "structured_request_button.setDisabled(False)" in success and "structured_request_button.setDisabled(False)" in failure


def test_legacy_and_structured_actions_remain_separate():
    assert "StructuredRecommendationWorker" not in inspect.getsource(MainWindow._start_llm_advice)
    assert "LLMAdviceWorker" not in inspect.getsource(MainWindow._start_structured_recommendation)
