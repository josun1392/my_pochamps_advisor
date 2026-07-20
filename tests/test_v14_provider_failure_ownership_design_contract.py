import inspect

from llm.advisor_client import run_ui_selected_advice


MIGRATION_STAGES = ("payload_builder", "fake_provider_adapter_tests", "structured_provider_entry_point", "complete_cycle_integration", "validated_ui_presentation", "t1_coexistence_decision")


def test_provider_failure_design_preserves_prepared_evidence_without_raw_response():
    prepared = {"candidates": [{"move": "move"}], "evidence_bundle": {"candidates": [{"move": "move"}]}}
    failure = {"status": "provider_unavailable", "prepared_cycle": prepared, "errors": ["provider_unavailable"]}
    assert failure["prepared_cycle"]["evidence_bundle"] == prepared["evidence_bundle"] and "raw_response" not in failure


def test_legacy_path_remains_separate_and_migration_stages_are_ordered():
    assert "prepare_ui_recommendation_cycle" not in inspect.getsource(run_ui_selected_advice)
    assert MIGRATION_STAGES[:2] == ("payload_builder", "fake_provider_adapter_tests") and MIGRATION_STAGES[-1] == "t1_coexistence_decision"
