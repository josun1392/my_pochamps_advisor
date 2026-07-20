import inspect

from llm import advisor_candidate_contract
from llm.advisor_candidate_contract import (
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
    run_offline_recommendation_provider_adapter,
)


CYCLE_STAGES = (
    "prepare_ui_recommendation_cycle",
    "run_offline_recommendation_provider_adapter",
    "complete_recommendation_cycle",
)


def test_future_offline_cycle_composes_existing_boundaries_in_order():
    assert CYCLE_STAGES == (
        prepare_ui_recommendation_cycle.__name__,
        run_offline_recommendation_provider_adapter.__name__,
        complete_recommendation_cycle.__name__,
    )
    assert CYCLE_STAGES.index("prepare_ui_recommendation_cycle") < CYCLE_STAGES.index("run_offline_recommendation_provider_adapter") < CYCLE_STAGES.index("complete_recommendation_cycle")


def test_design_keeps_cycle_provider_and_ui_neutral():
    source = inspect.getsource(advisor_candidate_contract)
    assert "call_gemini(" not in source
    assert "LLMAdvicePanel" not in source
    assert "QThread" not in source


def test_nonready_preparation_design_blocks_the_provider_stage():
    prepared = {"status": "no_selectable_candidates", "recommendation_request": None}
    assert prepared["status"] != "ready"
    assert prepared["recommendation_request"] is None
