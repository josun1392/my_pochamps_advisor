"""Approval-gated, redacted provider grounding for threat-aware self ranking."""
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

from llm.advisor_candidate_contract import build_provider_recommendation_payload, complete_recommendation_cycle, prepare_ui_recommendation_cycle, rank_direct_mechanics_candidates
from llm.advisor_client import SAFE_PROVIDER_DIAGNOSTIC_CODES, sanitize_provider_failure_context
from llm.advisor_threat_ranking import project_threat_ranking_tier
from scripts.run_sanitized_multi_move_mechanics_smoke import _Species, _battle, _current_hp, _provenance
from scripts.spike_advisor import DEFAULT_MODEL

FIXTURES = ("partial-known-confirmed-threat-ranking", "partial-known-neutral-no-safety-reward")
EXIT = {"ok": 0, "usage": 2, "credential": 3, "provider": 4, "parse": 5, "semantic": 7, "blocked": 9}


def _repository() -> dict[str, dict[str, Any]]:
    rows = (("slam", "physical", 100, "normal", "selected-pokemon", 0), ("quick", "physical", 40, "normal", "selected-pokemon", 1), ("earthquake", "physical", 100, "ground", "selected-pokemon", 0), ("protect", "status", None, "normal", "user", 4), ("tackle", "physical", 40, "normal", "selected-pokemon", 0))
    return {name: {key: value for key, value in {"move_id": name, "category": category, "power": power, "type": kind, "target": target, "priority": priority}.items() if value is not None} for name, category, power, kind, target, priority in rows}


def _prepared(fixture_id: str) -> dict[str, Any]:
    battle = _battle(known_action_order=True)
    battle["moves"]["my_available_moves"] = [{"slot_index": 0, "move_id": "slam"}, {"slot_index": 1, "move_id": "quick"}]
    known_move = "earthquake" if fixture_id == FIXTURES[0] else "protect"
    battle["known_move_context"] = {"schema_version": "known-move-context-v1", "session_id": "multi-smoke", "self": {"slot_index": 0, "pokemon_id": "pikachu", "state": "unknown", "known_move_ids": [], "unknown_slot_count": 4}, "opponent": {"slot_index": 1, "pokemon_id": "eevee", "state": "partially_known", "known_move_ids": [known_move], "unknown_slot_count": 3}}
    if fixture_id == FIXTURES[0]:
        battle["trusted_level_context"]["current_levels"].append({"side": "opponent", "value": 50, "provenance": _provenance("opponent", 1, "eevee", source="user_confirmed_current_level")})
        battle["current_hp_context"] = {"current_hp": [_current_hp("self", 1, 100), _current_hp("opponent", 1, 100)]}
        for entry in battle["final_stat_context"]["current_final_stats"]:
            if entry["stat"] == "speed": entry["value"] = 100 if entry["side"] == "self" else 200
    else:
        battle["current_hp_context"] = {"current_hp": [_current_hp("self", 100, 100), _current_hp("opponent", 1, 100)]}
    return prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "slam"}, {"move_id": "quick"}], battle_input=battle, move_repository=_repository(), species_repository=_Species())


def _ranks(rows: Sequence[Mapping[str, Any]]) -> dict[str, int | None]:
    return {str(row.get("move")): row.get("mechanics_comparison", {}).get("rank") for row in rows}


def _preflight(fixture_id: str, prepared: Mapping[str, Any], payload: Mapping[str, Any]) -> tuple[bool, tuple[str, int] | None]:
    request, bundle, candidates = prepared.get("recommendation_request"), prepared.get("evidence_bundle"), prepared.get("candidates")
    rows = request.get("candidate_comparisons") if isinstance(request, Mapping) else None
    summaries = bundle.get("known_opponent_threat_summaries", {}).get("threat_summaries", []) if isinstance(bundle, Mapping) else []
    if prepared.get("status") != "ready" or not isinstance(rows, list) or not isinstance(candidates, list) or len(rows) != len(candidates) != 2 or len(summaries) != 2:
        return False, None
    serialized = json.dumps(payload, sort_keys=True)
    if any(key in serialized for key in ("internal_threat_summaries", "opponent_action_candidates", "known_opponent_threat_summaries", "threat_ranking_tier")):
        return False, None
    base_comparisons = rank_direct_mechanics_candidates(candidates=candidates)
    base = {str(candidate.get("move")): base_comparisons.get((candidate.get("slot_index"), candidate.get("move")), {}).get("rank") for candidate in candidates}
    summary_by_id = {summary.get("self_candidate_id"): summary for summary in summaries if isinstance(summary, Mapping)}
    tiers = {key: project_threat_ranking_tier(value)[0] for key, value in summary_by_id.items()}
    common = all(row.get("eligibility") != "not_selectable" for row in rows) and all(summary.get("candidate_set_complete") is False and summary.get("unknown_slots_remaining") == 3 for summary in summaries if isinstance(summary, Mapping)) and payload.get("selectable_candidate_exact_set") == [{"slot_index": 0, "move": "slam"}, {"slot_index": 1, "move": "quick"}]
    if fixture_id == FIXTURES[0]:
        valid = common and base == {"slam": 1, "quick": 2} and _ranks(rows) == {"slam": 2, "quick": 1} and tiers == {"self:0:slam": "executed_guaranteed_ohko", "self:1:quick": "neutral_no_positive_threat_evidence"}
    else:
        valid = common and base == _ranks(rows) == {"slam": 1, "quick": 2} and set(tiers.values()) == {"neutral_no_positive_threat_evidence"}
    winner = next(((str(row.get("move")), row.get("slot_index")) for row in rows if row.get("mechanics_comparison", {}).get("rank") == 1), None)
    return valid and isinstance(winner, tuple) and isinstance(winner[1], int), winner


def _actual_adapters(*, model: str) -> tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]:
    def credential_available() -> bool: return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    def provider_call(payload: Mapping[str, Any]) -> dict[str, Any]:
        from llm.advisor_client import call_structured_recommendation_provider
        response, _usage = call_structured_recommendation_provider(provider_payload=payload, model=model)
        return response
    return credential_available, provider_call


def run_smoke(*, actual: bool = False, model: str | None = None, fixtures: Sequence[str] = FIXTURES, max_calls: int = 2, no_retry: bool = True, credential_available: Callable[[], bool] | None = None, provider_call: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    if not actual: return {"exit_code": EXIT["ok"], "provider_calls": 0, "results": []}
    if model != DEFAULT_MODEL or tuple(fixtures) != FIXTURES or max_calls != 2 or not no_retry: return {"exit_code": EXIT["usage"], "provider_calls": 0, "results": []}
    if credential_available is None or not credential_available(): return {"exit_code": EXIT["credential"], "provider_calls": 0, "results": []}
    if provider_call is None: return {"exit_code": EXIT["blocked"], "provider_calls": 0, "results": []}
    results: list[dict[str, str]] = []
    for fixture_id in FIXTURES:
        prepared = _prepared(fixture_id); payload = build_provider_recommendation_payload(prepared_cycle=prepared)
        valid, expected = _preflight(fixture_id, prepared, payload)
        if not valid or not isinstance(payload, Mapping) or "status" in payload or expected is None: return {"exit_code": EXIT["blocked"], "provider_calls": len(results), "fixture_id": fixture_id, "failure_category": "fixture_preflight_failure", "results": results}
        try: response = provider_call(payload)
        except Exception as error:
            code = getattr(error, "code", "provider_failure"); result: dict[str, Any] = {"exit_code": EXIT["provider"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "provider_failure", "diagnostic": code if isinstance(code, str) and code in SAFE_PROVIDER_DIAGNOSTIC_CODES else "provider_unknown_failure", "results": results}; context = sanitize_provider_failure_context(getattr(error, "safe_context", None)); result.update({"provider_diagnostic": context} if context else {}); return result
        if not isinstance(response, dict): return {"exit_code": EXIT["parse"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "structured_response_parse_failure", "results": results}
        completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=response); recommendation = completed.get("recommendation_result") if isinstance(completed, Mapping) else None; selected = (recommendation.get("recommended_move"), recommendation.get("recommended_slot_index")) if isinstance(recommendation, Mapping) else None
        if completed.get("status") != "resolved" or selected != expected: return {"exit_code": EXIT["semantic"], "provider_calls": len(results) + 1, "fixture_id": fixture_id, "failure_category": "ranking_selection_mismatch", "results": results}
        results.append({"fixture_id": fixture_id, "status": "passed"})
    return {"exit_code": EXIT["ok"], "provider_calls": len(results), "results": results}


def main(argv: Sequence[str] | None = None, *, adapter_factory: Callable[..., tuple[Callable[[], bool], Callable[[Mapping[str, Any]], dict[str, Any]]]] = _actual_adapters) -> int:
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument("--actual", action="store_true"); parser.add_argument("--model"); parser.add_argument("--fixtures", nargs="*"); parser.add_argument("--max-calls", type=int); parser.add_argument("--no-retry", action="store_true")
    args, _ = parser.parse_known_args(argv); kwargs: dict[str, Any] = {"actual": args.actual, "model": args.model, "fixtures": tuple(args.fixtures or FIXTURES), "max_calls": args.max_calls or 2, "no_retry": args.no_retry}
    if args.actual and args.model == DEFAULT_MODEL and args.no_retry:
        credential, provider = adapter_factory(model=args.model); kwargs.update(credential_available=credential, provider_call=provider)
    result = run_smoke(**kwargs); print(json.dumps({key: result[key] for key in ("fixture_id", "failure_category", "diagnostic", "provider_diagnostic", "exit_code", "provider_calls") if key in result}, separators=(",", ":"))); return int(result["exit_code"])


if __name__ == "__main__": raise SystemExit(main())
