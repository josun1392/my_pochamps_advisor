from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SENTINEL = "RAW_SECRET_RESPONSE_SENTINEL"
SCRIPT_MODULE = "scripts.run_sanitized_condition_smoke"


def _acknowledged_response(advice: str) -> str:
    return (
        "[Trusted Context]\n"
        "- Current condition | self | burn\n"
        "- Current condition | opponent | unknown\n"
        "- Observed item event | opponent | focus-sash | item_activation_observed\n\n"
        "[Advice]\n"
        f"{advice}"
    )


def _run_cli_harness(*, provider_body: str, evaluator_failure: bool = False, provider_failure: bool = False) -> subprocess.CompletedProcess[str]:
    provider_setup = (
        "raise RuntimeError('RAW_SECRET_RESPONSE_SENTINEL provider failure')"
        if provider_failure
        else f"return {provider_body!r}, {{'input_tokens': 101, 'output_tokens': 11, 'cached_tokens': 0}}"
    )
    evaluator_setup = (
        "smoke.evaluate_current_condition_item_event_response = "
        "lambda response: (_ for _ in ()).throw(RuntimeError('RAW_SECRET_RESPONSE_SENTINEL evaluator failure'))"
        if evaluator_failure
        else ""
    )
    code = f"""
import llm.advisor_client as advisor_client
import {SCRIPT_MODULE} as smoke

def fake_provider(prompt, model):
    {provider_setup}

advisor_client.call_gemini = fake_provider
advisor_client._log_advisor_call = lambda **kwargs: {{'estimated_cost_usd': 0.001}}
{evaluator_setup}
raise SystemExit(smoke.main(['--fixture', 'current-condition-item-event', '--model', 'offline-cli-test']))
"""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _result(process: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert process.stderr == ""
    lines = process.stdout.splitlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert set(result).issubset(
        {
            "schema_version",
            "provider_status",
            "semantic_status",
            "response_status",
            "summary",
            "model",
            "usage",
            "error_category",
        }
    )
    assert not {
        "raw_response",
        "response_text",
        "prompt",
        "request",
        "headers",
        "api_key",
        "credential",
        "environment",
        "stack_trace",
        "provider_raw_body",
    } & set(result)
    assert RAW_SENTINEL not in process.stdout
    assert RAW_SENTINEL not in process.stderr
    return result


def test_subprocess_cli_emits_one_sanitized_json_line_for_semantic_pass() -> None:
    response = _acknowledged_response(
        f"{RAW_SENTINEL} Choose cautiously; the acknowledgement does not establish resolved outcomes."
    )
    process = _run_cli_harness(provider_body=response)
    result = _result(process)

    assert process.returncode == 0
    assert result["provider_status"] == "success"
    assert result["semantic_status"] == "pass"
    assert result["response_status"] == "available"
    assert result["model"] == "offline-cli-test"
    assert result["usage"] == {
        "input_tokens": 101,
        "output_tokens": 11,
        "cached_tokens": 0,
        "estimated_cost_usd": 0.001,
    }


def test_subprocess_cli_reports_semantic_fail_without_echoing_response() -> None:
    response = _acknowledged_response(f"{RAW_SENTINEL} The opponent paralysis is known.")
    process = _run_cli_harness(provider_body=response)
    result = _result(process)

    assert process.returncode == 0
    assert result["provider_status"] == "success"
    assert result["semantic_status"] == "fail"
    assert result["response_status"] == "available"


def test_subprocess_cli_separates_response_unavailable_from_provider_failure() -> None:
    process = _run_cli_harness(provider_body="")
    result = _result(process)

    assert process.returncode == 5
    assert result["provider_status"] == "success"
    assert result["semantic_status"] == "unavailable"
    assert result["response_status"] == "unavailable"
    assert result["error_category"] == "response_unavailable"


def test_subprocess_cli_separates_evaluator_failure_without_traceback() -> None:
    response = _acknowledged_response(f"{RAW_SENTINEL} Advice remains cautious.")
    process = _run_cli_harness(provider_body=response, evaluator_failure=True)
    result = _result(process)

    assert process.returncode == 6
    assert result["provider_status"] == "success"
    assert result["semantic_status"] == "unavailable"
    assert result["response_status"] == "available"
    assert result["error_category"] == "evaluator_failure"


def test_subprocess_cli_reports_provider_failure_without_raw_exception_detail() -> None:
    process = _run_cli_harness(provider_body="", provider_failure=True)
    result = _result(process)

    assert process.returncode == 4
    assert result["provider_status"] == "failure"
    assert result["semantic_status"] == "not_evaluated"
    assert result["response_status"] == "unavailable"
    assert result["error_category"] == "provider_failure"


def test_subprocess_cli_rejects_invalid_fixture_without_non_json_output() -> None:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            SCRIPT_MODULE,
            "--fixture",
            "not-supported",
            "--model",
            "offline-cli-test",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    result = _result(process)

    assert process.returncode == 2
    assert result["provider_status"] == "not_called"
    assert result["semantic_status"] == "not_evaluated"
    assert result["error_category"] == "invalid_cli_input"


def test_subprocess_cli_rejects_malformed_capture_output_without_repr() -> None:
    code = f"""
import {SCRIPT_MODULE} as smoke

def malformed_runner(battle_input, evaluator, model):
    return object(), {{}}, {{}}

raise SystemExit(smoke.main(
    ['--fixture', 'current-condition-item-event', '--model', 'offline-cli-test'],
    smoke_runner=malformed_runner,
))
"""
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    result = _result(process)

    assert process.returncode == 2
    assert result["provider_status"] == "not_called"
    assert result["semantic_status"] == "not_evaluated"
    assert result["error_category"] == "preflight_failure"
