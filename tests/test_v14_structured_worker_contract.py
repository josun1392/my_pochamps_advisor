import inspect

from ui.main_window import LLMAdviceWorker, StructuredRecommendationWorker


def test_structured_worker_is_separate_and_copies_ui_inputs():
    worker = StructuredRecommendationWorker([{"move_id": "tackle"}], {"pokemon": {}}, object())
    assert worker._selected_moves == [{"move_id": "tackle"}]
    assert "run_ui_selected_advice" in inspect.getsource(LLMAdviceWorker.run)
    assert "run_structured_ui_recommendation" in inspect.getsource(StructuredRecommendationWorker.run)


def test_structured_worker_emits_sanitized_failure_only():
    source = inspect.getsource(StructuredRecommendationWorker.run)
    assert "except Exception" in source and "str(exc)" not in source and "traceback" not in source
