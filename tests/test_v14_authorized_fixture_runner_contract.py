import importlib.util
from pathlib import Path

import pytest

from llm.structured_fixture_evaluation import (
    PROVIDER_EVALUATION_STATE,
    CLEAR_RESOLVED_CALLS_CONSUMED,
    REMAINING_AUTHORIZED_CALL_BUDGET,
    UNCERTAIN_TIMEOUT_CALLS_CONSUMED,
    execute_single_authorized_fixture,
    prepare_single_authorized_fixture,
    suspended_fixture_report,
)


def _load_cli_module():
    path = Path("scripts/run_v14_17_fixture_evaluation.py")
    spec = importlib.util.spec_from_file_location("v1417_suspended_cli", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _resolved_response():
    return {"recommendation_status": "resolved", "recommended_move": "hyper-beam", "recommended_slot_index": 1, "primary_reasons": [], "risks": [], "alternatives": []}


def _usage():
    return {"input_tokens": 1, "output_tokens": 2, "cached_tokens": 0, "model": "sanitized", "tool": "structured_recommendation", "success": True, "failure_code": None}


def test_default_cli_and_actual_flag_are_suspended_without_provider_import_or_call(capsys):
    cli = _load_cli_module()
    assert cli.main([]) == 0
    assert json_status(capsys.readouterr().out) == "suspended"
    assert cli.main(["--actual-provider-approved", "--fixture", "clear_resolved"]) == 2
    assert json_status(capsys.readouterr().out) == "provider_evaluation_suspended"
    source = Path("scripts/run_v14_17_fixture_evaluation.py").read_text(encoding="utf-8")
    assert source.index("from llm.advisor_client") > source.index("if not preflight[\"provider_eligible\"]")


def json_status(output):
    import json
    return json.loads(output)["status"]


def test_missing_unknown_multiple_and_budget_override_requests_cannot_create_provider():
    cli = _load_cli_module()
    with pytest.raises(SystemExit):
        cli.parse_args(["--fixture", "unknown"])
    assert cli.main(["--fixture", "clear_resolved", "--fixture", "insufficient_context"]) == 2
    assert cli.main(["--budget", "3"]) == 2
    assert PROVIDER_EVALUATION_STATE == "SUSPENDED"
    assert UNCERTAIN_TIMEOUT_CALLS_CONSUMED == 1 and CLEAR_RESOLVED_CALLS_CONSUMED == 1
    assert REMAINING_AUTHORIZED_CALL_BUDGET == 1


def test_suspended_and_order_rejections_happen_before_provider_factory_creation():
    created = []
    factory = lambda: created.append("created") or (lambda **_: (_resolved_response(), _usage()))
    suspended = execute_single_authorized_fixture(
        fixture_id="clear_resolved", completed_fixture_ids=(), actual_provider_approved=False,
        provider_evaluation_state=PROVIDER_EVALUATION_STATE, provider_factory=factory, model="sanitized",
    )
    assert suspended["status"] == "suspended" and created == []
    with pytest.raises(ValueError, match="fixture_order_not_authorized"):
        execute_single_authorized_fixture(
            fixture_id="insufficient_context", completed_fixture_ids=(), actual_provider_approved=True,
            provider_evaluation_state="ACTIVE", provider_factory=factory, model="sanitized",
        )
    assert created == []


def test_insufficient_context_requires_completed_sanitized_predecessor_before_factory_creation():
    created = []
    with pytest.raises(ValueError, match="predecessor_not_authorized"):
        execute_single_authorized_fixture(
            fixture_id="insufficient_context", completed_fixture_ids=("clear_resolved",),
            actual_provider_approved=True, provider_evaluation_state="ACTIVE",
            provider_factory=lambda: created.append("created"), model="sanitized",
        )
    assert created == []


def test_clear_resolved_one_shot_uses_fake_provider_once_only_after_no_provider_preflight():
    cli = _load_cli_module()
    preflight = prepare_single_authorized_fixture(fixture_id="clear_resolved", completed_fixture_ids=())
    created, calls = [], []
    def provider(**_):
        calls.append("called")
        return _resolved_response(), _usage()
    result = cli.run_t1_clear_resolved_once(provider_factory=lambda: created.append("created") or provider, model="sanitized")
    assert preflight["provider_eligible"] is True
    assert created == ["created"] and calls == ["called"] and result["actual_call_count"] == 1


def test_insufficient_context_one_shot_uses_fake_provider_once_after_predecessor_and_preflight():
    cli = _load_cli_module()
    created, calls = [], []
    def provider(**_):
        calls.append("called")
        return {"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": []}, _usage()
    result = cli.run_t1_insufficient_context_once(
        provider_factory=lambda: created.append("created") or provider, model="sanitized",
    )
    assert created == ["created"] and calls == ["called"]
    assert result["actual_call_count"] == 1 and result["completion_status"] == "insufficient_context"
    assert result["remaining_call_budget"] == 0 and result["recommended_move"] is None


def test_blocked_fixture_never_creates_or_calls_provider_after_all_single_fixture_guards():
    created = []
    result = execute_single_authorized_fixture(
        fixture_id="no_selectable_candidates", completed_fixture_ids=("clear_resolved", "insufficient_context"),
        actual_provider_approved=True, provider_evaluation_state="ACTIVE",
        provider_factory=lambda: created.append("created"), model="sanitized",
    )
    assert result["completion_status"] == "blocked" and result["provider_invoked"] is False and created == []


def test_preparation_failure_never_creates_or_calls_provider(monkeypatch):
    import llm.structured_fixture_evaluation as evaluation
    monkeypatch.setattr(evaluation, "prepare_ui_recommendation_cycle", lambda **_: {"status": "invalid_snapshot", "errors": ["invalid_battle_snapshot"], "evidence_bundle": None})
    created = []
    result = evaluation.execute_single_authorized_fixture(
        fixture_id="clear_resolved", completed_fixture_ids=(), actual_provider_approved=True,
        provider_evaluation_state="ACTIVE", provider_factory=lambda: created.append("created"), model="sanitized",
    )
    assert result["completion_status"] == "blocked" and result["provider_invoked"] is False and created == []


@pytest.mark.parametrize("mode", ["resolved", "timeout", "exception", "invalid"])
def test_single_fixture_terminal_outcomes_have_one_call_no_retry_or_fallback(mode):
    calls = []
    class Failure(Exception):
        code = "provider_timeout"
    def provider(**_):
        calls.append("called")
        if mode == "timeout":
            raise Failure()
        if mode == "exception":
            raise RuntimeError("secret-like-message-is-not-returned")
        if mode == "invalid":
            return {"unexpected": "shape"}, _usage()
        return _resolved_response(), _usage()
    result = execute_single_authorized_fixture(
        fixture_id="clear_resolved", completed_fixture_ids=(), actual_provider_approved=True,
        provider_evaluation_state="ACTIVE", provider_factory=lambda: provider, model="sanitized",
    )
    assert calls == ["called"] and result["actual_call_count"] == 1
    assert result["completion_status"] in {"resolved", "timeout_uncertain", "provider_unavailable", "provider_response_validation_failed"}
    assert "secret-like-message" not in str(result) and "provider_factory" not in result


def test_sanitized_suspended_report_never_contains_raw_provider_or_credential_fields():
    report = suspended_fixture_report(fixture_id="clear_resolved")
    assert report["actual_call_count"] == 0 and report["provider_invoked"] is False
    assert all(forbidden not in str(report).lower() for forbidden in ("raw_response", "provider_payload", "api_key", "credential", "traceback"))
