import importlib.util
from pathlib import Path

from llm.structured_fixture_evaluation import (
    REMAINING_AUTHORIZED_CALL_BUDGET,
    get_fixture_coverage_inventory,
)


def _load_cli_module():
    path = Path("scripts/run_v14_17_fixture_evaluation.py")
    spec = importlib.util.spec_from_file_location("v1418_closed_cli", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_inventory_has_exactly_ten_unique_explicit_provider_independent_fixture_records():
    inventory = get_fixture_coverage_inventory()
    assert len(inventory) == 10
    assert len({entry["fixture_id"] for entry in inventory}) == 10
    assert all(entry["expected_terminal_category"] for entry in inventory)
    assert all(entry["provider_independent"] is True for entry in inventory)
    assert all(entry["schema_contract"] for entry in inventory)
    assert all(entry["semantic_contract"] for entry in inventory)


def test_actual_evidence_and_preparation_blocked_boundaries_are_not_overclaimed():
    by_id = {entry["fixture_id"]: entry for entry in get_fixture_coverage_inventory()}
    assert by_id["clear_resolved"]["provider_evidence"] == "actual_provider_passed"
    assert by_id["insufficient_context"]["provider_evidence"] == "actual_provider_passed"
    assert by_id["insufficient_context"]["recommendation_expected"] is False
    assert by_id["insufficient_context"]["historical_sanitized_failure_categories"] == ("invalid_claim",)
    assert by_id["no_selectable_candidates"]["provider_evidence"] == "preparation_blocked"
    assert by_id["no_selectable_candidates"]["selectable_candidates_expected"] is False
    assert all(entry["provider_evidence"] != "actual_provider_passed" or entry["actual_invocation_count"] == 1 for entry in by_id.values())


def test_closed_budget_default_cli_and_budget_override_cannot_create_provider(capsys):
    cli = _load_cli_module()
    assert REMAINING_AUTHORIZED_CALL_BUDGET == 0
    assert cli.main([]) == 0
    assert '"status": "suspended"' in capsys.readouterr().out
    assert cli.main(["--execute-t1-insufficient-context-once"]) == 2
    assert '"status": "provider_budget_exhausted"' in capsys.readouterr().out
    assert cli.main(["--budget", "3"]) == 2
    assert '"status": "budget_override_rejected"' in capsys.readouterr().out
    source = Path("scripts/run_v14_17_fixture_evaluation.py").read_text(encoding="utf-8")
    assert "from llm.advisor_client" not in source
