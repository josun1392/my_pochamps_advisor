"""Emit one sanitized current-condition smoke attempt as one JSON line.

This CLI is intentionally single-attempt. It uses the normal advisor capture
path and never writes provider response text to stdout, stderr, or a file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import llm.advisor_client as advisor_client  # noqa: E402


SCHEMA_VERSION = 1
FIXTURE_NAME = "current-condition-item-event"
DEFAULT_MODEL = "gemini-2.5-flash"

EXIT_SUCCESS = 0
EXIT_PREFLIGHT_FAILURE = 2
EXIT_CREDENTIAL_UNAVAILABLE = 3
EXIT_PROVIDER_FAILURE = 4
EXIT_RESPONSE_UNAVAILABLE = 5
EXIT_EVALUATOR_FAILURE = 6

_ALLOWED_KEYS = frozenset(
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
_FORBIDDEN_KEYS = frozenset(
    {
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
    }
)

SmokeRunner = Callable[
    [dict[str, Any], Callable[[str], tuple[str, str]], str],
    tuple[advisor_client.SanitizedSmokeResponseCapture, dict[str, int], dict[str, Any]],
]


def build_current_condition_item_event_fixture() -> dict[str, Any]:
    """Return the fixed raw fixture; confidence is added only by normalization."""
    fixture = {
        "scenario": {
            "attacker_side": "self",
            "defender_side": "opponent",
            "format_note": "Limited current-condition and observed-item-event smoke fixture.",
            "known_limitations": [
                "Current conditions are user-confirmed present-state context only.",
                "Observed item events do not establish resolved effects.",
            ],
        },
        "pokemon": {
            "self": {"hp_percent": 100},
            "opponent": {"hp_percent": 100},
        },
    }
    fixture["current_condition_confirmations"] = [
        {
            "side": "self",
            "condition_type": "burn",
            "status": "user_confirmed",
            "source": "user_confirmed_current_condition",
        },
        {
            "side": "opponent",
            "condition_type": "unknown",
            "status": "user_confirmed",
            "source": "user_confirmed_current_condition",
        },
    ]
    fixture["item_event_confirmations"] = [
        {
            "side": "opponent",
            "item": "focus-sash",
            "event_type": "item_activation_observed",
            "status": "user_confirmed",
            "source": "explicit_user_event_confirmation",
            "turn": None,
            "note": None,
        }
    ]
    return fixture


def evaluate_current_condition_item_event_response(response: str) -> tuple[str, str]:
    """Evaluate only the fixed smoke fixture without retaining response text."""
    text = response.lower()
    required = (
        "self" in text and "burn" in text and "user-confirmed" in text and "current" in text,
        "opponent" in text and "unknown" in text,
        "focus sash" in text and "observed" in text and "activation" in text,
    )
    forbidden = (
        "burn was applied this turn",
        "burn damage triggered this turn",
        "exact status damage",
        "post-turn hp is",
        "sleep turns remaining",
        "freeze thaw roll",
        "full paralysis occurred",
        "rng roll",
        "final speed order",
        "focus sash left the pokemon at exactly 1 hp",
        "focus sash left the pokémon at exactly 1 hp",
        "resolved item effect",
    )
    opponent_unknown_inference = re.search(
        r"opponent[^.]{0,100}\b(paralysis|paralyzed|poison|poisoned|toxic|sleep|asleep|freeze|frozen)\b",
        text,
    )
    if all(required) and not opponent_unknown_inference and not any(claim in text for claim in forbidden):
        return (
            "pass",
            "Self burn, opponent unknown, and the separate Focus Sash observation were acknowledged without resolved outcomes.",
        )
    return (
        "fail",
        "Current-condition or observed-item-event attribution was missing, mixed, or overstated.",
    )


def _default_smoke_runner(
    battle_input: dict[str, Any],
    evaluator: Callable[[str], tuple[str, str]],
    model: str,
) -> tuple[advisor_client.SanitizedSmokeResponseCapture, dict[str, int], dict[str, Any]]:
    return advisor_client.run_ui_selected_advice_with_sanitized_smoke_capture(
        battle_input,
        evaluator,
        model=model,
        enable_battle_state_context=True,
    )


def _usage_payload(usage: dict[str, int], session_summary: dict[str, Any]) -> dict[str, int | float]:
    cost = session_summary.get("estimated_cost_usd", 0.0)
    return {
        "input_tokens": max(0, int(usage.get("input_tokens", 0))),
        "output_tokens": max(0, int(usage.get("output_tokens", 0))),
        "cached_tokens": max(0, int(usage.get("cached_tokens", 0))),
        "estimated_cost_usd": max(0.0, float(cost)) if isinstance(cost, (int, float)) else 0.0,
    }


def _result_payload(
    *,
    provider_status: str,
    semantic_status: str,
    response_status: str,
    summary: str,
    model: str,
    usage: dict[str, int] | None = None,
    session_summary: dict[str, Any] | None = None,
    error_category: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provider_status": provider_status,
        "semantic_status": semantic_status,
        "response_status": response_status,
        "summary": " ".join(summary.split())[:240],
        "model": model,
        "usage": _usage_payload(usage or {}, session_summary or {}),
    }
    if error_category is not None:
        result["error_category"] = error_category
    _validate_result_payload(result)
    return result


def _validate_result_payload(result: dict[str, Any]) -> None:
    if set(result) - _ALLOWED_KEYS or set(result) & _FORBIDDEN_KEYS:
        raise ValueError("sanitized smoke result has disallowed keys")
    if result.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported schema version")
    if result.get("provider_status") not in {"success", "failure", "not_called"}:
        raise ValueError("unsupported provider status")
    if result.get("semantic_status") not in {"pass", "fail", "unavailable", "not_evaluated"}:
        raise ValueError("unsupported semantic status")
    if result.get("response_status") not in {"available", "unavailable"}:
        raise ValueError("unsupported response status")
    if not isinstance(result.get("summary"), str) or not isinstance(result.get("model"), str):
        raise ValueError("summary and model must be strings")
    if not isinstance(result.get("usage"), dict):
        raise ValueError("usage must be an object")


def _parse_args(argv: list[str]) -> tuple[str, str] | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fixture")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    try:
        args, extra = parser.parse_known_args(argv)
    except SystemExit:
        return None
    if extra or args.fixture != FIXTURE_NAME or not isinstance(args.model, str) or not args.model.strip():
        return None
    return args.fixture, args.model


def _emit(result: dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))


def main(argv: list[str] | None = None, *, smoke_runner: SmokeRunner = _default_smoke_runner) -> int:
    parsed = _parse_args(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        _emit(
            _result_payload(
                provider_status="not_called",
                semantic_status="not_evaluated",
                response_status="unavailable",
                summary="CLI input did not match the fixed smoke fixture contract.",
                model=DEFAULT_MODEL,
                error_category="invalid_cli_input",
            )
        )
        return EXIT_PREFLIGHT_FAILURE

    _, model = parsed
    try:
        capture, usage, session_summary = smoke_runner(
            build_current_condition_item_event_fixture(),
            evaluate_current_condition_item_event_response,
            model,
        )
    except Exception:
        result = _result_payload(
            provider_status="failure",
            semantic_status="not_evaluated",
            response_status="unavailable",
            summary="Provider attempt did not produce an evaluable result.",
            model=model,
            error_category="provider_failure",
        )
        _emit(result)
        return EXIT_PROVIDER_FAILURE

    try:
        if capture.provider_status != "provider_success":
            raise ValueError("capture provider status diverged from production contract")
        semantic_status = {
            "pass": "pass",
            "fail": "fail",
            "response_unavailable": "unavailable",
        }.get(capture.semantic_status)
        if semantic_status is None:
            raise ValueError("capture semantic status diverged from production contract")
        response_status = capture.response_status
        error_category = capture.error_category
        result = _result_payload(
            provider_status="success",
            semantic_status=semantic_status,
            response_status=response_status,
            summary=capture.sanitized_summary,
            model=model,
            usage=usage,
            session_summary=session_summary,
            error_category=error_category,
        )
    except (AttributeError, TypeError, ValueError):
        result = _result_payload(
            provider_status="not_called",
            semantic_status="not_evaluated",
            response_status="unavailable",
            summary="Sanitized capture output did not match the CLI contract.",
            model=model,
            error_category="preflight_failure",
        )
        _emit(result)
        return EXIT_PREFLIGHT_FAILURE

    _emit(result)
    if result.get("error_category") == "evaluator_failure":
        return EXIT_EVALUATOR_FAILURE
    if result["response_status"] == "unavailable":
        return EXIT_RESPONSE_UNAVAILABLE
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
