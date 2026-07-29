"""Approval-gated runtime-grounding smoke runner; defaults to no-network mode."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.advisor_candidate_contract import validate_runtime_grounding
from scripts.spike_advisor import DEFAULT_MODEL

REQUIRED_FIXTURES = ("runtime-unknown-bootstrap", "runtime-known-item-stale-ui")
OPTIONAL_FIXTURE = "runtime-partial-known-hp"
APPROVED_MODELS = frozenset({DEFAULT_MODEL})
EXIT = {"ok": 0, "usage": 2, "credential": 3, "provider": 4, "parse": 5, "structural": 6, "semantic": 7, "redaction": 8, "blocked": 9}
STRUCTURAL_GROUNDING_CODES = frozenset({"grounding_missing", "grounding_not_mapping", "grounding_version_missing", "grounding_version_invalid", "grounding_entries_missing", "grounding_entries_not_list", "grounding_entry_not_mapping", "grounding_entry_field_missing", "grounding_entry_field_invalid", "grounding_unknown_field"})
SEMANTIC_GROUNDING_CODES = frozenset({"grounding_fact_missing_or_duplicate", "unknown_misclassification", "unknown_promoted", "runtime_fact_contradiction"})


def _runtime() -> dict[str, Any]:
    return {"field": {"weather": {"status": "unknown"}}}


def _grounding() -> dict[str, Any]:
    return {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [{"path": "field.weather"}], "evidence_only": [], "conflicts": [], "conditional_dependencies": []}


def build_actual_adapters(*, model: str) -> tuple[Callable[[], bool], Callable[[str], dict[str, Any]]]:
    """Create actual-only seams after CLI validation; never call them here."""
    def credential_available() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    def provider_call(fixture_id: str) -> dict[str, Any]:
        from llm.advisor_client import call_structured_recommendation_provider
        payload = {"request_version": "v14.3", "battle_snapshot_summary": {"fixture_id": fixture_id}, "candidate_exact_set": [], "selectable_candidate_exact_set": [], "candidate_comparisons": [], "known_limitations": ["sanitized smoke"], "guardrails": {"no_untrusted_inference": True}, "runtime_advice_state": _runtime()}
        response, _usage = call_structured_recommendation_provider(provider_payload=payload, model=model)
        return response
    return credential_available, provider_call


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
        except Exception: return {"exit_code": EXIT["provider"], "provider_calls": len(results) + 1, "network_calls": 0, "results": results, "fixture_id": fixture_id, "failure_category": "provider_failure"}
        if not isinstance(response, dict):
            return {"exit_code": EXIT["parse"], "provider_calls": len(results) + 1, "network_calls": 0, "results": results, "fixture_id": fixture_id, "failure_category": "structured_response_parse_failure"}
        errors = validate_runtime_grounding(runtime_advice_state=_runtime(), grounding=response.get("grounding") if isinstance(response, dict) else None)
        if errors:
            if any("internal" in error for error in errors): code = EXIT["redaction"]
            elif any(error in STRUCTURAL_GROUNDING_CODES for error in errors): code = EXIT["structural"]
            else: code = EXIT["semantic"]
            diagnostic = next((error for error in errors if error in STRUCTURAL_GROUNDING_CODES), None)
            semantic_diagnostic = next((error for error in errors if error in SEMANTIC_GROUNDING_CODES), None)
            category = "internal_metadata_exposure" if code == EXIT["redaction"] else "grounding_structural_failure" if code == EXIT["structural"] else "grounding_semantic_failure"
            return {"exit_code": code, "provider_calls": len(results) + 1, "network_calls": 0, "results": results, "fixture_id": fixture_id, "failure_category": category, "structural_diagnostic": diagnostic, "semantic_diagnostic": semantic_diagnostic}
        results.append({"fixture_id": fixture_id, "status": "passed"})
    return {"exit_code": EXIT["ok"], "provider_calls": len(results), "network_calls": 0, "results": results}


def _cli_surface(result: dict[str, Any]) -> dict[str, Any]:
    """Expose only bounded smoke status, never provider material or exceptions."""
    allowed = ("fixture_id", "failure_category", "structural_diagnostic", "semantic_diagnostic", "exit_code", "provider_calls")
    return {key: result[key] for key in allowed if key in result and result[key] is not None}


def main(argv: Sequence[str] | None = None, *, actual_adapter_factory: Callable[..., tuple[Callable[[], bool], Callable[[str], dict[str, Any]]]] = build_actual_adapters) -> int:
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument("--actual", action="store_true"); parser.add_argument("--model"); parser.add_argument("--fixtures", nargs="*"); parser.add_argument("--max-calls", type=int); parser.add_argument("--no-retry", action="store_true")
    args, _ = parser.parse_known_args(argv)
    kwargs = {"actual": args.actual, "model": args.model, "fixtures": tuple(args.fixtures or REQUIRED_FIXTURES), "max_calls": args.max_calls or 2, "no_retry": args.no_retry}
    if args.actual and args.model in APPROVED_MODELS and args.no_retry:
        credential_available, provider_call = actual_adapter_factory(model=args.model)
        kwargs.update(credential_available=credential_available, provider_call=provider_call)
    result = run_smoke(**kwargs)
    print(json.dumps(_cli_surface(result), separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__": raise SystemExit(main())
