"""Approval-gated actual smoke for provider grounding of direct mechanics evidence."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm.advisor_candidate_contract import (
    build_provider_recommendation_payload,
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
)
from llm.advisor_client import SAFE_PROVIDER_DIAGNOSTIC_CODES, sanitize_provider_failure_context
from scripts.spike_advisor import DEFAULT_MODEL

FIXTURES = ("complete-direct-mechanics", "insufficient-direct-mechanics")
EXIT = {"ok": 0, "usage": 2, "credential": 3, "provider": 4, "parse": 5, "structural": 6, "semantic": 7, "redaction": 8, "blocked": 9}


class _Species:
    def get(self, name: str) -> dict[str, Any]:
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in ("hp", "attack", "defense", "special-attack", "special-defense", "speed")}}


def _provenance(side: str, slot: int, pokemon: str, *, source: str = "user_confirmed_final_battle_stat") -> dict[str, Any]:
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "direct-smoke", "source": source, "trust": "user_confirmed_current"}


def _direct_context(*, incomplete: bool) -> dict[str, Any]:
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "status": absent, "boosts": {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed")}, "current_hp": 100, "max_hp": 100}
    result = {"generation": "gen9", "attacker": dict(side), "defender": dict(side), "field": {"weather": absent, "terrain": absent}}
    if incomplete:
        result["defender"] = dict(result["defender"])
        result["defender"]["item"] = {"status": "unknown"}
    return result


def _battle(*, incomplete: bool) -> dict[str, Any]:
    entries = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        entries.extend({"side": side, "stat": stat, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)} for index, stat in enumerate(("hp", "attack", "defense", "special-attack", "special-defense", "speed")))
    return {"current_state_session_id": "direct-smoke", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}, "final_stat_context": {"current_final_stats": entries}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": _provenance("self", 0, "pikachu", source="user_confirmed_current_level")}]}, "direct_mechanics_context": _direct_context(incomplete=incomplete)}


def _prepared(fixture_id: str) -> dict[str, Any]:
    if fixture_id not in FIXTURES:
        raise ValueError("invalid_fixture")
    return prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=_battle(incomplete=fixture_id == FIXTURES[1]), move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}}, species_repository=_Species())


def _actual_adapters(*, model: str) -> tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]:
    def credential_available() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    def provider_call(payload: Mapping[str, Any]) -> dict[str, Any]:
        from llm.advisor_client import call_structured_recommendation_provider
        response, _usage = call_structured_recommendation_provider(provider_payload=payload, model=model)
        return response
    return credential_available, provider_call


def run_smoke(*, actual: bool = False, model: str | None = None, fixtures: Sequence[str] = FIXTURES, max_calls: int = 2, no_retry: bool = True, credential_available: Callable[[], bool] | None = None, provider_call: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    selected = tuple(fixtures)
    if not actual:
        return {"exit_code": EXIT["ok"], "provider_calls": 0, "results": []}
    if model != DEFAULT_MODEL or not no_retry or selected not in (FIXTURES[:1], FIXTURES) or max_calls != len(selected):
        return {"exit_code": EXIT["usage"], "provider_calls": 0, "results": []}
    if credential_available is None or not credential_available():
        return {"exit_code": EXIT["credential"], "provider_calls": 0, "results": []}
    if provider_call is None:
        return {"exit_code": EXIT["blocked"], "provider_calls": 0, "results": []}
    results: list[dict[str, Any]] = []
    for fixture_id in selected:
        prepared = _prepared(fixture_id)
        candidate = prepared.get("candidates", [{}])[0] if isinstance(prepared.get("candidates"), list) else {}
        mechanics = candidate.get("mechanics_result") if isinstance(candidate, Mapping) else None
        expected = "known" if fixture_id == FIXTURES[0] else "insufficient_context"
        if not isinstance(mechanics, Mapping) or mechanics.get("status") != expected:
            return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "fixture_preparation_failure", "results": results}
        payload = build_provider_recommendation_payload(prepared_cycle=prepared)
        if not isinstance(payload, Mapping) or "status" in payload:
            return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "payload_preparation_failure", "results": results}
        try:
            response = provider_call(payload)
        except Exception as error:
            code = getattr(error, "code", "provider_failure")
            diagnostic = code if isinstance(code, str) and code in SAFE_PROVIDER_DIAGNOSTIC_CODES else "provider_unknown_failure"
            safe_context = sanitize_provider_failure_context(getattr(error, "safe_context", None))
            result = {"exit_code": EXIT["provider"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "provider_failure", "diagnostic": diagnostic, "results": results}
            if safe_context:
                result["provider_diagnostic"] = safe_context
            return result
        if not isinstance(response, dict):
            return {"exit_code": EXIT["parse"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "structured_response_parse_failure", "results": results}
        completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=response)
        if completed.get("status") not in {"resolved", "insufficient_context", "no_usable_candidate"}:
            errors = completed.get("errors") if isinstance(completed.get("errors"), list) else []
            category = "grounding_structural_failure" if any(str(error).startswith("grounding_") for error in errors) else "grounding_semantic_failure"
            return {"exit_code": EXIT["structural"] if category == "grounding_structural_failure" else EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": category, "diagnostic": next((error for error in errors if isinstance(error, str)), "validation_failed"), "results": results}
        if fixture_id == FIXTURES[1] and completed.get("status") != "insufficient_context":
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "insufficient_context_not_preserved", "diagnostic": "insufficient_context_not_preserved", "results": results}
        results.append({"fixture_id": fixture_id, "status": "passed", "mechanics_status": expected})
    return {"exit_code": EXIT["ok"], "provider_calls": len(results), "results": results}


def _surface(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in ("fixture_id", "failure_category", "diagnostic", "provider_diagnostic", "exit_code", "provider_calls") if key in result}


def main(argv: Sequence[str] | None = None, *, adapter_factory: Callable[..., tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]] = _actual_adapters) -> int:
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument("--actual", action="store_true"); parser.add_argument("--model"); parser.add_argument("--fixtures", nargs="*"); parser.add_argument("--max-calls", type=int); parser.add_argument("--no-retry", action="store_true")
    args, _ = parser.parse_known_args(argv)
    kwargs: dict[str, Any] = {"actual": args.actual, "model": args.model, "fixtures": tuple(args.fixtures or FIXTURES), "max_calls": args.max_calls or 2, "no_retry": args.no_retry}
    if args.actual and args.model == DEFAULT_MODEL and args.no_retry:
        credential, provider = adapter_factory(model=args.model)
        kwargs.update(credential_available=credential, provider_call=provider)
    result = run_smoke(**kwargs)
    print(json.dumps(_surface(result), separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
