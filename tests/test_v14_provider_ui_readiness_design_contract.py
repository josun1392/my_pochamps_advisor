import inspect

import llm.advisor_candidate_contract as contract
from llm.advisor_client import run_ui_selected_advice


MIGRATION_STAGES = ("pure_ui_snapshot_adapter", "offline_prepare_integration", "provider_adapter", "offline_completion_presentation", "coexistence_decision")


def test_pure_cycle_and_current_selected_move_provider_path_remain_separate():
    pure_source = inspect.getsource(contract)
    provider_source = inspect.getsource(run_ui_selected_advice)
    assert "call_gemini" not in pure_source and "ui." not in pure_source
    assert "prepare_recommendation_cycle" not in provider_source
    assert MIGRATION_STAGES[:3] == ("pure_ui_snapshot_adapter", "offline_prepare_integration", "provider_adapter")


def test_design_scope_excludes_ranking_turn_engine_and_direct_ui_provider_calls():
    forbidden = {"ranking", "turn_engine", "provider_call_from_ui", "raw_response_display"}
    design = {"pure_cycle", "provider_adapter_future", "ui_adapter_future"}
    assert not (forbidden & design)
