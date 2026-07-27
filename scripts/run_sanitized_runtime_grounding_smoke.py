"""Approval-gated runtime-grounding smoke runner; defaults to no-network mode."""
from __future__ import annotations

import argparse
from typing import Any, Callable, Sequence

from llm.advisor_candidate_contract import validate_runtime_grounding
from scripts.spike_advisor import DEFAULT_MODEL

REQUIRED_FIXTURES = ("runtime-unknown-bootstrap", "runtime-known-item-stale-ui")
OPTIONAL_FIXTURE = "runtime-partial-known-hp"
APPROVED_MODELS = frozenset({DEFAULT_MODEL})
EXIT = {"ok": 0, "usage": 2, "credential": 3, "provider": 4, "parse": 5, "structural": 6, "semantic": 7, "redaction": 8, "blocked": 9}


def _runtime() -> dict[str, Any]:
    return {"field": {"weather": {"status": "unknown"}}}


def _grounding() -> dict[str, Any]:
    return {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [{"path": "field.weather"}], "evidence_only": [], "conflicts": [], "conditional_dependencies": []}


def run_smoke(*, actual: bool = False, model: str | None = None, fixtures: Sequence[str] = REQUIRED_FIXTURES, max_calls: int = 2, no_retry: bool = True, provider_call: Callable[[str], dict[str, Any]] | None = None, credential_available: Callable[[], bool] | None = None) -> dict[str, Any]:
    selected = tuple(fixtures)
    if not actual:
        return {"exit_code": EXIT["ok"], "provider_calls": 0, "network_calls": 0, "results": []}
    if not model or model not in APPROVED_MODELS or not no_retry or not selected or len(set(selected)) != len(selected) or any(item not in (*REQUIRED_FIXTURES, OPTIONAL_FIXTURE) for item in selected) or max_calls not in {2, 3} or len(selected) > max_calls or (OPTIONAL_FIXTURE in selected and max_calls != 3):
        return {"exit_code": EXIT["usage"], "provider_calls": 0, "network_calls": 0, "results": []}
    if credential_available is None or not credential_available():
        return {"exit_code": EXIT["credential"], "provider_calls": 0, "network_calls": 0, "results": []}
    if provider_call is None:
        return {"exit_code": EXIT["blocked"], "provider_calls": 0, "network_calls": 0, "results": []}
    results = []
    for fixture_id in selected:
        try: response = provider_call(fixture_id)
        except Exception: return {"exit_code": EXIT["provider"], "provider_calls": len(results) + 1, "network_calls": 0, "results": results}
        if not isinstance(response, dict):
            return {"exit_code": EXIT["parse"], "provider_calls": len(results) + 1, "network_calls": 0, "results": results}
        errors = validate_runtime_grounding(runtime_advice_state=_runtime(), grounding=response.get("grounding") if isinstance(response, dict) else None)
        if errors:
            if any("internal" in error for error in errors): code = EXIT["redaction"]
            elif any(error in {"invalid_grounding", "invalid_grounding_entry", "grounding_required"} for error in errors): code = EXIT["structural"]
            else: code = EXIT["semantic"]
            return {"exit_code": code, "provider_calls": len(results) + 1, "network_calls": 0, "results": results}
        results.append({"fixture_id": fixture_id, "status": "passed"})
    return {"exit_code": EXIT["ok"], "provider_calls": len(results), "network_calls": 0, "results": results}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument("--actual", action="store_true"); parser.add_argument("--model"); parser.add_argument("--fixtures", nargs="*"); parser.add_argument("--max-calls", type=int); parser.add_argument("--no-retry", action="store_true")
    args, _ = parser.parse_known_args(argv)
    result = run_smoke(actual=args.actual, model=args.model, fixtures=tuple(args.fixtures or REQUIRED_FIXTURES), max_calls=args.max_calls or 2, no_retry=args.no_retry)
    return int(result["exit_code"])


if __name__ == "__main__": raise SystemExit(main())
