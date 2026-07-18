from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import llm.advisor_client as advisor_client
import scripts.run_sanitized_condition_smoke as smoke_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SENTINEL = "RAW_SECRET_RESPONSE_SENTINEL"
SCRIPT_MODULE = "scripts.run_sanitized_condition_smoke"


def _acknowledged_response(advice: str, *, ability_fixture: bool = False) -> str:
    ability_lines = ""
    if ability_fixture:
        ability_lines = (
            "- Current ability | self | intimidate\n"
            "- Current ability | opponent | unknown\n"
        )
    return (
        "[Trusted Context]\n"
        "- Current condition | self | burn\n"
        "- Current condition | opponent | unknown\n"
        + ability_lines
        + "- Observed item event | opponent | focus-sash | item_activation_observed\n\n"
        "[Advice]\n"
        f"{advice}"
    )


def test_sanitized_evaluator_optionally_exact_checks_deterministic_damage_results() -> None:
    expected = (("damage_estimate", "self", "opponent", "tackle", "40-48", "base-damage-stage-only"),)
    response = (
        "[Trusted Context]\n\n[Deterministic Results]\n"
        "- Damage estimate | self | opponent | tackle | 40-48 | base-damage-stage-only\n\n"
        "[Advice]\nThe limited range is unresolved outside the declared scope."
    )
    assert smoke_cli.evaluate_current_condition_item_event_response(
        response, expected_entries=(), expected_result_entries=expected
    )[0] == "pass"
    assert smoke_cli.evaluate_current_condition_item_event_response(
        response.replace("40-48", "41-48"), expected_entries=(), expected_result_entries=expected
    )[0] == "fail"


def _run_cli_harness(
    *,
    provider_body: str,
    fixture: str = "current-condition-item-event",
    evaluator_failure: bool = False,
    provider_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
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
raise SystemExit(smoke.main(['--fixture', {fixture!r}, '--model', 'offline-cli-test']))
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


def test_ability_fixture_is_raw_but_normalizes_all_three_trusted_context_categories() -> None:
    fixture = smoke_cli.build_current_condition_ability_item_event_fixture()

    assert all("confidence" not in entry for entry in fixture["current_condition_confirmations"])
    assert all("confidence" not in entry for entry in fixture["current_ability_confirmations"])
    assert all("confidence" not in entry for entry in fixture["item_event_confirmations"])

    prompt = advisor_client._build_ui_selected_prompt(fixture, enable_battle_state_context=True)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    assert payload["condition_context"]["current_conditions"] == [
        {**entry, "confidence": "known"} for entry in fixture["current_condition_confirmations"]
    ]
    assert payload["ability_context"]["current_abilities"] == [
        {**entry, "confidence": "known"} for entry in fixture["current_ability_confirmations"]
    ]
    assert payload["item_event_context"]["observed_events"] == [
        {**fixture["item_event_confirmations"][0], "confidence": "observed"}
    ]
    assert advisor_client.build_trusted_context_acknowledgement_entries(payload) == (
        ("current_condition", "self", "burn", None),
        ("current_condition", "opponent", "unknown", None),
        ("current_ability", "self", "intimidate", None),
        ("current_ability", "opponent", "unknown", None),
        ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"),
    )
    for required_line in (
        "- Current condition | self | burn",
        "- Current condition | opponent | unknown",
        "- Current ability | self | intimidate",
        "- Current ability | opponent | unknown",
        "- Observed item event | opponent | focus-sash | item_activation_observed",
        "[Advice]",
    ):
        assert required_line in prompt
    for forbidden_field in (
        "ability_activated_this_turn",
        "ability_triggered_this_turn",
        "ability_suppressed",
        "ability_replaced",
        "ability_copied",
        "resolved_ability_effect",
        "exact_stat_change",
        "exact_damage_modifier",
        "exact_damage",
        "exact_post_turn_hp",
        "boosted_stat",
        "final_speed_order",
        "immunity_resolved",
        "prevention_resolved",
        "rng_roll",
        "post_turn_ability_state",
        "condition_applied_this_turn",
        "condition_triggered_this_turn",
        "resolved_condition_effect",
        "resolved_item_effect",
        "focus_sash_post_hit_hp_1",
    ):
        assert forbidden_field not in prompt


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


def test_subprocess_cli_ability_fixture_preserves_normalized_exact_set_without_raw_response() -> None:
    response = _acknowledged_response(
        f"{RAW_SENTINEL} Intimidate is only a confirmed current identity; choose cautiously because activation and stat changes are not confirmed.",
        ability_fixture=True,
    )
    process = _run_cli_harness(
        provider_body=response,
        fixture="current-condition-ability-item-event",
    )
    result = _result(process)

    assert process.returncode == 0
    assert result["provider_status"] == "success"
    assert result["semantic_status"] == "pass"
    assert result["response_status"] == "available"


@pytest.mark.parametrize(
    "response",
    [
        _acknowledged_response("Choose cautiously.", ability_fixture=False),
        _acknowledged_response(
            "Opponent current ability is levitate, so choose cautiously.", ability_fixture=True
        ),
        _acknowledged_response(
            "Intimidate activated this turn and opponent Attack was definitely lowered.", ability_fixture=True
        ),
    ],
)
def test_subprocess_cli_ability_fixture_rejects_missing_or_unsupported_ability_claims(response: str) -> None:
    process = _run_cli_harness(
        provider_body=f"{RAW_SENTINEL} {response}",
        fixture="current-condition-ability-item-event",
    )
    result = _result(process)

    assert process.returncode == 0
    assert result["provider_status"] == "success"
    assert result["semantic_status"] == "fail"
    assert result["response_status"] == "available"


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
