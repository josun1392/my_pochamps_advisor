"""Approval-gated, redacted smoke for deterministic multi-move mechanics ranking."""
from __future__ import annotations

import argparse
from copy import deepcopy
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
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
)
from llm.advisor_client import SAFE_PROVIDER_DIAGNOSTIC_CODES, format_recommendation_presentation_text, sanitize_provider_failure_context
from scripts.spike_advisor import DEFAULT_MODEL

FIXTURES = ("multi-move-clear-winner", "multi-move-mixed-availability", "multi-move-stable-tie")
GROUNDING_FIXTURES = ("complete-multi-candidate-mechanics", "mixed-context-multi-candidate-mechanics")
_ALLOWED_FIXTURE_SETS = frozenset({FIXTURES, GROUNDING_FIXTURES})
EXIT = {"ok": 0, "usage": 2, "credential": 3, "provider": 4, "parse": 5, "structural": 6, "semantic": 7, "redaction": 8, "blocked": 9}


class _Species:
    def get(self, name: str) -> dict[str, Any]:
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in ("hp", "attack", "defense", "special-attack", "special-defense", "speed")}}


def _provenance(side: str, slot: int, pokemon: str, *, source: str = "user_confirmed_final_battle_stat") -> dict[str, Any]:
    return {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "multi-smoke", "source": source, "trust": "user_confirmed_current"}


def _battle(*, known_action_order: bool = False) -> dict[str, Any]:
    entries = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        entries.extend({"side": side, "stat": stat, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": _provenance(side, slot, pokemon)} for index, stat in enumerate(("hp", "attack", "defense", "special-attack", "special-defense", "speed")))
    absent = {"status": "known_absent"}
    side = {"ability": absent, "item": absent, "status": absent, "boosts": {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed")}, "current_hp": 100, "max_hp": 100}
    battle = {"current_state_session_id": "multi-smoke", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": []}, "final_stat_context": {"current_final_stats": entries}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": _provenance("self", 0, "pikachu", source="user_confirmed_current_level")}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": deepcopy(side), "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}}}
    if known_action_order:
        battle["opponent_selected_move"] = {"move_id": "tackle"}
        battle["field_state_context"] = {"current_field": {"weather": "none", "terrain": "none", "global_effects": [], "side_effects": [], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}}
    return battle


def _fixture(fixture_id: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if fixture_id == FIXTURES[0]:
        return [{"move_id": "tackle"}, {"move_id": "slam"}], {"tackle": {"category": "physical", "power": 40, "type": "normal"}, "slam": {"category": "physical", "power": 100, "type": "normal"}}
    if fixture_id == FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "missing-power"}, {"move_id": "double-hit"}], {"tackle": {"category": "physical", "power": 40, "type": "normal"}, "missing-power": {"category": "physical", "type": "normal"}, "double-hit": {"category": "physical", "power": 35, "type": "normal", "min_hits": 2, "max_hits": 2}}
    if fixture_id == FIXTURES[2]:
        return [{"move_id": "tackle"}, {"move_id": "tackle"}], {"tackle": {"category": "physical", "power": 40, "type": "normal"}}
    if fixture_id == GROUNDING_FIXTURES[0]:
        return [{"move_id": "quick-attack"}, {"move_id": "slam"}], {"quick-attack": {"category": "physical", "power": 40, "type": "normal", "priority": 1}, "slam": {"category": "physical", "power": 100, "type": "normal", "priority": 0}, "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    if fixture_id == GROUNDING_FIXTURES[1]:
        return [{"move_id": "tackle"}, {"move_id": "missing-power"}, {"move_id": "double-hit"}], {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "missing-power": {"category": "physical", "type": "normal", "priority": 0}, "double-hit": {"category": "physical", "power": 35, "type": "normal", "min_hits": 2, "max_hits": 2, "priority": 0}}
    raise ValueError("invalid_fixture")


def _prepared(fixture_id: str) -> dict[str, Any]:
    moves, repository = _fixture(fixture_id)
    battle = _battle(known_action_order=fixture_id in GROUNDING_FIXTURES)
    battle["moves"]["my_available_moves"] = [{"slot_index": index, "move_id": item["move_id"]} for index, item in enumerate(moves)]
    return prepare_ui_recommendation_cycle(selected_moves=moves, battle_input=battle, move_repository=repository, species_repository=_Species())


def _expected_rank_one(payload: Mapping[str, Any]) -> tuple[str, int] | None:
    comparisons = payload.get("candidate_comparisons")
    if not isinstance(comparisons, list):
        return None
    winners = [(row.get("move"), row.get("slot_index")) for row in comparisons if isinstance(row, Mapping) and isinstance(row.get("mechanics_comparison"), Mapping) and row["mechanics_comparison"].get("rank") == 1]
    if len(winners) != 1 or not isinstance(winners[0][0], str) or not isinstance(winners[0][1], int):
        return None
    return winners[0]


def _fixture_contract_valid(fixture_id: str, payload: Mapping[str, Any]) -> bool:
    rows = payload.get("candidate_comparisons")
    if not isinstance(rows, list):
        return False
    comparisons = [row.get("mechanics_comparison") for row in rows if isinstance(row, Mapping)]
    if fixture_id == FIXTURES[0]:
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [2, 1] and all(isinstance(row.get("mechanics_result"), Mapping) and row["mechanics_result"].get("status") == "known" for row in rows if isinstance(row, Mapping))
    if fixture_id == FIXTURES[1]:
        mechanics = [row.get("mechanics_result") for row in rows if isinstance(row, Mapping)]
        return [item.get("comparison_status") for item in comparisons if isinstance(item, Mapping)] == ["rankable", "insufficient_context", "unsupported_mechanic"] and [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, None, None] and isinstance(mechanics[1], Mapping) and isinstance(mechanics[1].get("missing_inputs"), list) and bool(mechanics[1]["missing_inputs"]) and isinstance(mechanics[2], Mapping) and isinstance(mechanics[2].get("unsupported_reason"), str)
    if fixture_id == FIXTURES[2]:
        return [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, 2]
    if fixture_id == GROUNDING_FIXTURES[0]:
        if [item.get("rank") for item in comparisons if isinstance(item, Mapping)] != [2, 1]:
            return False
        return all(
            isinstance(row, Mapping)
            and isinstance(row.get("mechanics_result"), Mapping)
            and row["mechanics_result"].get("status") == "known"
            and isinstance(row.get("comparison_facts"), Mapping)
            and row["comparison_facts"].get("candidate_id") == {"slot_index": row.get("slot_index"), "move": row.get("move")}
            for row in rows
        ) and any(row["comparison_facts"].get("action_order_status") == "acts_first" for row in rows)
    if fixture_id == GROUNDING_FIXTURES[1]:
        mechanics = [row.get("mechanics_result") for row in rows if isinstance(row, Mapping)]
        return [item.get("comparison_status") for item in comparisons if isinstance(item, Mapping)] == ["rankable", "insufficient_context", "unsupported_mechanic"] and [item.get("rank") for item in comparisons if isinstance(item, Mapping)] == [1, None, None] and all(isinstance(row.get("comparison_facts"), Mapping) and row["comparison_facts"].get("candidate_id") == {"slot_index": row.get("slot_index"), "move": row.get("move")} for row in rows if isinstance(row, Mapping)) and isinstance(mechanics[1], Mapping) and isinstance(mechanics[1].get("missing_inputs"), list) and bool(mechanics[1]["missing_inputs"]) and isinstance(mechanics[2], Mapping) and isinstance(mechanics[2].get("unsupported_reason"), str)
    return False


def _completed_candidate_evidence_isolated(*, payload: Mapping[str, Any], completed: Mapping[str, Any]) -> bool:
    """Confirm completion retained each candidate's own native evidence only."""
    rows, candidates = payload.get("candidate_comparisons"), completed.get("candidates")
    if not isinstance(rows, list) or not isinstance(candidates, list) or len(rows) != len(candidates):
        return False
    indexed = {(candidate.get("slot_index"), candidate.get("move")): candidate for candidate in candidates if isinstance(candidate, Mapping)}
    if len(indexed) != len(candidates):
        return False
    for row in rows:
        if not isinstance(row, Mapping):
            return False
        pair = (row.get("slot_index"), row.get("move"))
        candidate = indexed.get(pair)
        facts = row.get("comparison_facts")
        if not isinstance(candidate, Mapping) or not isinstance(facts, Mapping):
            return False
        if facts.get("candidate_id") != {"slot_index": pair[0], "move": pair[1]}:
            return False
        if candidate.get("mechanics_result") != row.get("mechanics_result") or candidate.get("action_order") != row.get("action_order"):
            return False
    return True


def _presentation_contract_valid(*, fixture_id: str, completed: Mapping[str, Any]) -> bool:
    result = completed.get("recommendation_result")
    if not isinstance(result, Mapping) or result.get("status") != "resolved":
        return False
    selected = result.get("selected_candidate_evidence")
    action = result.get("selected_action")
    facts = selected.get("comparison_facts") if isinstance(selected, Mapping) else None
    if not isinstance(selected, Mapping) or not isinstance(action, Mapping) or not isinstance(facts, Mapping) or facts.get("candidate_id") != action:
        return False
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    summary = presentation.get("selected_candidate") if isinstance(presentation, Mapping) else None
    if not isinstance(summary, Mapping) or summary.get("selected_action") != action:
        return False
    text = format_recommendation_presentation_text(presentation_model=presentation)
    forbidden = ("candidate_comparisons", "raw_response", "mechanics_path", "numeric_scope", "multi_provider_")
    if not isinstance(text, str) or any(item in text for item in forbidden) or "선택 행동:" not in text:
        return False
    mechanics = selected.get("mechanics_result")
    if isinstance(mechanics, Mapping) and mechanics.get("status") == "known":
        return "피해 범위:" in text and "피해 비율:" in text
    return "피해 범위:" not in text and "피해 비율:" not in text


def _actual_adapters(*, model: str) -> tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]:
    def credential_available() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    def provider_call(payload: Mapping[str, Any]) -> dict[str, Any]:
        from llm.advisor_client import call_structured_recommendation_provider
        response, _usage = call_structured_recommendation_provider(provider_payload=payload, model=model)
        return response

    return credential_available, provider_call


def run_smoke(*, actual: bool = False, model: str | None = None, fixtures: Sequence[str] = FIXTURES, max_calls: int = 3, no_retry: bool = True, credential_available: Callable[[], bool] | None = None, provider_call: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    selected = tuple(fixtures)
    if not actual:
        return {"exit_code": EXIT["ok"], "provider_calls": 0, "results": []}
    if model != DEFAULT_MODEL or not no_retry or selected not in _ALLOWED_FIXTURE_SETS or max_calls != len(selected):
        return {"exit_code": EXIT["usage"], "provider_calls": 0, "results": []}
    if credential_available is None or not credential_available():
        return {"exit_code": EXIT["credential"], "provider_calls": 0, "results": []}
    if provider_call is None:
        return {"exit_code": EXIT["blocked"], "provider_calls": 0, "results": []}
    results: list[dict[str, Any]] = []
    for fixture_id in selected:
        prepared = _prepared(fixture_id)
        payload = build_provider_recommendation_payload(prepared_cycle=prepared)
        if prepared.get("status") != "ready" or not isinstance(payload, Mapping) or "status" in payload or not _fixture_contract_valid(fixture_id, payload):
            return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "fixture_preparation_failure", "results": results}
        expected = _expected_rank_one(payload)
        if expected is None:
            return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "ranking_contract_failure", "results": results}
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
        if completed.get("status") != "resolved":
            errors = completed.get("errors") if isinstance(completed.get("errors"), list) else []
            category = "grounding_structural_failure" if any(str(error).startswith("grounding_") for error in errors) else "grounding_semantic_failure"
            return {"exit_code": EXIT["structural"] if category == "grounding_structural_failure" else EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": category, "diagnostic": next((error for error in errors if isinstance(error, str)), "validation_failed"), "results": results}
        if not _completed_candidate_evidence_isolated(payload=payload, completed=completed):
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "multi_candidate_evidence_mixed", "diagnostic": "multi_candidate_evidence_mixed", "results": results}
        if not _presentation_contract_valid(fixture_id=fixture_id, completed=completed):
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "presentation_contract_invalid", "diagnostic": "presentation_contract_invalid", "results": results}
        recommendation = completed.get("recommendation_result")
        if not isinstance(recommendation, Mapping) or (recommendation.get("recommended_move"), recommendation.get("recommended_slot_index")) != expected:
            return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "ranking_selection_mismatch", "diagnostic": "ranking_selection_mismatch", "results": results}
        results.append({"fixture_id": fixture_id, "status": "passed"})
    return {"exit_code": EXIT["ok"], "provider_calls": len(results), "results": results}


def _surface(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in ("fixture_id", "failure_category", "diagnostic", "provider_diagnostic", "exit_code", "provider_calls") if key in result}


def main(argv: Sequence[str] | None = None, *, adapter_factory: Callable[..., tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]] = _actual_adapters) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--actual", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--fixtures", nargs="*")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--no-retry", action="store_true")
    args, _ = parser.parse_known_args(argv)
    kwargs: dict[str, Any] = {"actual": args.actual, "model": args.model, "fixtures": tuple(args.fixtures or FIXTURES), "max_calls": args.max_calls or 3, "no_retry": args.no_retry}
    if args.actual and args.model == DEFAULT_MODEL and args.no_retry:
        credential, provider = adapter_factory(model=args.model)
        kwargs.update(credential_available=credential, provider_call=provider)
    result = run_smoke(**kwargs)
    print(json.dumps(_surface(result), separators=(",", ":")))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
