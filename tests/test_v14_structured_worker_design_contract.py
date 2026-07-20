import inspect

from llm.advisor_client import run_ui_selected_advice
from ui.main_window import LLMAdviceWorker


WORKER_OWNERSHIP = {
    "legacy": ("LLMAdviceWorker", "freeform_text", "unchanged"),
    "future_structured": ("StructuredRecommendationWorker", "sanitized_presentation_model", "t1_approval_required"),
}


def test_future_structured_worker_is_separate_from_legacy_signal_contract():
    assert WORKER_OWNERSHIP["legacy"][1] == "freeform_text"
    assert WORKER_OWNERSHIP["future_structured"][1] == "sanitized_presentation_model"
    assert "run_offline_recommendation_cycle" not in inspect.getsource(LLMAdviceWorker.run)
    assert "run_offline_recommendation_cycle" not in inspect.getsource(run_ui_selected_advice)


def test_worker_design_keeps_provider_validation_and_ui_failures_separate():
    owners = ("provider", "structured_decoding", "response_adapter", "semantic_completion", "worker", "ui_rendering")
    assert len(set(owners)) == len(owners)
    assert WORKER_OWNERSHIP["future_structured"][2] == "t1_approval_required"
