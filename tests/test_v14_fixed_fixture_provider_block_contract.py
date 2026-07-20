from pathlib import Path

from llm.structured_fixture_evaluation import evaluate_structured_fixture, get_fixed_fixture_catalog


def test_provider_blocked_fixtures_never_enter_response_adapter_or_completion():
    blocked = [evaluate_structured_fixture(fixture=fixture) for fixture in get_fixed_fixture_catalog() if not fixture["provider_invocation_allowed"]]
    assert len(blocked) == 2
    assert all(not result["provider_allowed"] and result["decoded_status"] is None and result["completion_status"] is None for result in blocked)
    assert {result["preparation_status"] for result in blocked} == {"no_candidates", "no_selectable_candidates"}


def test_fixture_runner_has_no_provider_network_or_legacy_runtime_dependency():
    source = Path("llm/structured_fixture_evaluation.py").read_text(encoding="utf-8")
    assert "requests" not in source and "call_structured_recommendation_provider" not in source
    assert "run_ui_selected_advice" not in source and "call_gemini" not in source
