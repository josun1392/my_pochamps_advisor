import inspect

from llm.advisor_client import call_structured_recommendation_provider, run_structured_ui_recommendation
from ui.main_window import StructuredRecommendationWorker


def test_structured_sources_exclude_retry_fallback_and_raw_content_handoffs():
    source = inspect.getsource(call_structured_recommendation_provider) + inspect.getsource(run_structured_ui_recommendation)
    assert "call_gemini" not in source and "retry" not in source and "raw_response" not in source


def test_worker_and_runtime_have_no_secret_or_traceback_emission():
    source = inspect.getsource(StructuredRecommendationWorker.run) + inspect.getsource(run_structured_ui_recommendation)
    for forbidden in ("api_key", "authorization", "credential", "traceback", "stack_trace"):
        assert forbidden not in source
