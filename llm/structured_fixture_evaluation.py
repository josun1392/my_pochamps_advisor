"""Pure fixed-fixture evaluation for the structured recommendation contract."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_candidate_contract import (
    adapt_provider_recommendation_response,
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
)


_RECOMMENDATION_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate"})


def _stat(side: str, stat: str, value: int) -> dict[str, Any]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _battle(*, resolved: bool) -> dict[str, Any]:
    result = {
        "scenario": {"mode": "advisor", "known_limitations": ["Sanitized fixed-fixture limitation."]},
        "pokemon": {"my_active": {"name_en": "fixture_self"}, "opponent_active": {"name_en": "fixture_opponent"}},
    }
    if resolved:
        result["final_stat_context"] = {"current_final_stats": [
            _stat("self", "attack", 200), _stat("self", "special-attack", 200), _stat("self", "speed", 200),
            _stat("opponent", "defense", 150), _stat("opponent", "special-defense", 150), _stat("opponent", "speed", 100),
        ]}
    return result


def _repository() -> dict[str, dict[str, Any]]:
    return {
        "tackle": {"category": "physical", "power": 40, "type": "normal"},
        "hyper-beam": {"category": "special", "power": 150, "type": "normal"},
    }


def _response(status: str, *, move: str | None = None, slot: int | None = None, reasons: list[dict[str, str]] | None = None, alternatives: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "recommendation_status": status,
        "recommended_move": move,
        "recommended_slot_index": slot,
        "primary_reasons": [] if reasons is None else reasons,
        "risks": [],
        "alternatives": [] if alternatives is None else alternatives,
    }


def get_fixed_fixture_catalog() -> tuple[dict[str, Any], ...]:
    """Return independently copyable, sanitized fixture definitions."""
    moves = [{"move_id": "tackle"}, {"move_id": "hyper-beam"}]
    resolved_base = {"selected_moves": moves, "battle_input": _battle(resolved=True), "move_repository": _repository(), "expected_preparation_status": "ready", "expected_selectable_count": 2, "provider_invocation_allowed": True}
    catalog = (
        {"fixture_id": "clear_resolved", **resolved_base, "provider_response": _response("resolved", move="hyper-beam", slot=1), "expected_recommendation_status": "resolved", "expected_semantic_result": "passed", "expected_failure_code": None, "expected_pair": {"move": "hyper-beam", "slot_index": 1}},
        {"fixture_id": "close_resolved", **resolved_base, "provider_response": _response("resolved", move="tackle", slot=0), "expected_recommendation_status": "resolved", "expected_semantic_result": "passed", "expected_failure_code": None, "expected_pair": {"move": "tackle", "slot_index": 0}},
        {"fixture_id": "insufficient_context", "selected_moves": moves, "battle_input": _battle(resolved=False), "move_repository": _repository(), "provider_response": _response("insufficient_context", reasons=[{"kind": "partial_context", "claim": "limited deterministic evidence"}]), "expected_preparation_status": "ready", "expected_selectable_count": 2, "expected_recommendation_status": "insufficient_context", "expected_semantic_result": "passed", "expected_failure_code": None, "expected_pair": None, "provider_invocation_allowed": True},
        {"fixture_id": "no_selectable_candidates", "selected_moves": [{"move_id": "missing-a"}, {"move_id": "missing-b"}], "battle_input": _battle(resolved=False), "move_repository": {}, "provider_response": None, "expected_preparation_status": "no_selectable_candidates", "expected_selectable_count": 0, "expected_recommendation_status": "no_usable_candidate", "expected_semantic_result": "provider_blocked", "expected_failure_code": "no_selectable_candidates", "expected_pair": None, "provider_invocation_allowed": False},
        {"fixture_id": "invalid_alternative", **resolved_base, "provider_response": _response("resolved", move="hyper-beam", slot=1, alternatives=[{"move": "missing", "slot_index": 3, "reason": {"kind": "partial_context", "claim": "sanitized"}}]), "expected_recommendation_status": "validation_failed", "expected_semantic_result": "failed", "expected_failure_code": "selection outside selectable exact-set", "expected_pair": None},
        {"fixture_id": "slot_mismatch", **resolved_base, "provider_response": _response("resolved", move="hyper-beam", slot=0), "expected_recommendation_status": "validation_failed", "expected_semantic_result": "failed", "expected_failure_code": "recommended_candidate_not_selectable", "expected_pair": None},
        {"fixture_id": "unsupported_claim", **resolved_base, "provider_response": _response("resolved", move="hyper-beam", slot=1, reasons=[{"kind": "unsupported", "claim": "sanitized"}]), "expected_recommendation_status": "validation_failed", "expected_semantic_result": "failed", "expected_failure_code": "invalid_claim", "expected_pair": None},
        {"fixture_id": "partial_context_valid", "selected_moves": moves, "battle_input": _battle(resolved=False), "move_repository": _repository(), "provider_response": _response("insufficient_context", reasons=[{"kind": "partial_context", "claim": "limited deterministic evidence"}]), "expected_preparation_status": "ready", "expected_selectable_count": 2, "expected_recommendation_status": "insufficient_context", "expected_semantic_result": "passed", "expected_failure_code": None, "expected_pair": None, "provider_invocation_allowed": True},
        {"fixture_id": "partial_context_contradiction", **resolved_base, "provider_response": _response("resolved", move="hyper-beam", slot=1, reasons=[{"kind": "partial_context", "claim": "missing deterministic evidence"}]), "expected_recommendation_status": "validation_failed", "expected_semantic_result": "failed", "expected_failure_code": "claim_evidence_contradiction", "expected_pair": None},
        {"fixture_id": "no_usable_candidate", "selected_moves": [], "battle_input": _battle(resolved=False), "move_repository": {}, "provider_response": None, "expected_preparation_status": "no_candidates", "expected_selectable_count": 0, "expected_recommendation_status": "no_usable_candidate", "expected_semantic_result": "provider_blocked", "expected_failure_code": "no_candidates", "expected_pair": None, "provider_invocation_allowed": False},
    )
    return deepcopy(catalog)


def evaluate_structured_fixture(*, fixture: Mapping[str, Any], provider_response: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate one fixed fixture through existing pure production boundaries."""
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=fixture["selected_moves"], battle_input=fixture["battle_input"], move_repository=fixture["move_repository"],
    )
    request = prepared.get("recommendation_request")
    selectable = request.get("readiness", {}).get("selectable_candidate_count", 0) if isinstance(request, Mapping) else 0
    provider_allowed = prepared.get("status") == "ready" and isinstance(request, Mapping)
    base = {
        "fixture_id": fixture["fixture_id"], "preparation_status": prepared.get("status"), "provider_allowed": provider_allowed,
        "selectable_count": selectable, "decoded_status": None, "completion_status": None, "semantic_success": False,
        "expected_status_match": prepared.get("status") == fixture["expected_preparation_status"], "recommended_pair_match": False,
        "failure_codes": list(prepared.get("errors", [])), "presentation_status": None, "evidence_preserved": isinstance(prepared.get("evidence_bundle"), Mapping),
    }
    if not provider_allowed:
        base["recommended_pair_match"] = fixture.get("expected_pair") is None
        return base
    response = provider_response if provider_response is not None else fixture.get("provider_response")
    adapted = adapt_provider_recommendation_response(provider_response=response)
    if adapted.get("status") == "provider_response_validation_failed":
        base.update(decoded_status="provider_response_validation_failed", completion_status="provider_response_validation_failed", failure_codes=list(adapted.get("errors", [])))
        return base
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=adapted)
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    result = completed.get("recommendation_result") if isinstance(completed.get("recommendation_result"), Mapping) else {}
    pair = {"move": result.get("recommended_move"), "slot_index": result.get("recommended_slot_index")} if result.get("recommended_move") is not None else None
    expected_pair = fixture.get("expected_pair")
    completion_status = completed.get("status")
    base.update(
        decoded_status=adapted.get("recommendation_status"), completion_status=completion_status,
        semantic_success=completion_status in _RECOMMENDATION_STATUSES,
        expected_status_match=completion_status == fixture["expected_recommendation_status"],
        recommended_pair_match=pair == expected_pair,
        failure_codes=list(completed.get("errors", [])), presentation_status=presentation.get("status"),
        evidence_preserved=isinstance(completed.get("evidence_bundle"), Mapping),
    )
    return base


def aggregate_structured_fixture_results(*, results: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize deterministic fixture results without reliability claims."""
    failures: dict[str, int] = {}
    for result in results:
        for code in result.get("failure_codes", []):
            if isinstance(code, str):
                failures[code] = failures.get(code, 0) + 1
    return {
        "fixture_count": len(results),
        "preparation_ready_count": sum(result.get("preparation_status") == "ready" for result in results),
        "provider_blocked_count": sum(not result.get("provider_allowed") for result in results),
        "decode_success_count": sum(result.get("decoded_status") in _RECOMMENDATION_STATUSES for result in results),
        "semantic_success_count": sum(bool(result.get("semantic_success")) for result in results),
        "expected_status_match_count": sum(bool(result.get("expected_status_match")) for result in results),
        "exact_pair_success_count": sum(bool(result.get("recommended_pair_match")) and result.get("completion_status") == "resolved" for result in results),
        "failure_distribution": failures,
    }
