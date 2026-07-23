"""Pure fixed-fixture evaluation for the structured recommendation contract."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from llm.advisor_candidate_contract import (
    adapt_provider_recommendation_response,
    build_provider_recommendation_payload,
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
)


_RECOMMENDATION_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate"})
AUTHORIZED_ACTUAL_FIXTURE_IDS = ("clear_resolved", "insufficient_context", "no_selectable_candidates")
ORIGINAL_AUTHORIZED_CALL_BUDGET = 3
UNCERTAIN_TIMEOUT_CALLS_CONSUMED = 1
CLEAR_RESOLVED_CALLS_CONSUMED = 1
# The earlier uncertain timeout and the completed clear-resolved evaluation
# are both conservatively consumed.  This module never accepts a CLI budget
# override; a T1-scoped one-shot caller may only consume this final call.
REMAINING_AUTHORIZED_CALL_BUDGET = 1
PROVIDER_EVALUATION_STATE = "SUSPENDED"
_FIXTURE_PREDECESSORS = {
    "clear_resolved": (),
    "insufficient_context": ("clear_resolved",),
    "no_selectable_candidates": ("clear_resolved", "insufficient_context"),
}
_SANITIZED_PROVIDER_FAILURES = frozenset({
    "provider_unavailable", "provider_timeout", "provider_safety_blocked", "provider_response_missing",
    "provider_response_malformed", "provider_structured_decode_failed", "provider_response_validation_failed",
})
_SAFE_USAGE_KEYS = ("input_tokens", "output_tokens", "cached_tokens", "model", "tool", "success", "failure_code")
_CLEAR_RESOLVED_PREDECESSOR = {
    "terminal_status": "resolved",
    "schema_validation": True,
    "semantic_validation": True,
    "fixture_evaluation": True,
    "provider_invocation_count": 1,
    "retry_count": 0,
    "fallback_count": 0,
    "repair_count": 0,
    "legacy_fallback_count": 0,
}


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


def _sanitized_usage(usage: Any) -> dict[str, Any]:
    if not isinstance(usage, Mapping):
        return {}
    return {key: deepcopy(usage[key]) for key in _SAFE_USAGE_KEYS if key in usage and type(usage[key]) in {str, int, bool, type(None)}}


def _single_authorized_fixture(*, fixture_id: str, completed_fixture_ids: Sequence[str]) -> Mapping[str, Any]:
    if fixture_id not in AUTHORIZED_ACTUAL_FIXTURE_IDS:
        raise ValueError("unauthorized_fixture")
    if tuple(completed_fixture_ids) != _FIXTURE_PREDECESSORS[fixture_id]:
        raise ValueError("fixture_order_not_authorized")
    return next(fixture for fixture in get_fixed_fixture_catalog() if fixture["fixture_id"] == fixture_id)


def validate_clear_resolved_predecessor(*, evidence: Mapping[str, Any] | None) -> bool:
    """Accept only the sanitized, completed clear-resolved predecessor record."""
    return isinstance(evidence, Mapping) and all(evidence.get(key) == value for key, value in _CLEAR_RESOLVED_PREDECESSOR.items())


def suspended_fixture_report(*, fixture_id: str | None = None) -> dict[str, Any]:
    """Return a no-call terminal report while actual-provider evaluation is suspended."""
    if fixture_id is not None and fixture_id not in AUTHORIZED_ACTUAL_FIXTURE_IDS:
        raise ValueError("unauthorized_fixture")
    return {
        "status": "suspended", "fixture_id": fixture_id, "provider_invoked": False,
        "actual_call_count": 0, "remaining_call_budget": REMAINING_AUTHORIZED_CALL_BUDGET,
        "timeout_calls_consumed": UNCERTAIN_TIMEOUT_CALLS_CONSUMED,
    }


def prepare_single_authorized_fixture(
    *, fixture_id: str, completed_fixture_ids: Sequence[str], predecessor_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform the no-provider portion of a single-fixture authorization check."""
    fixture = _single_authorized_fixture(fixture_id=fixture_id, completed_fixture_ids=completed_fixture_ids)
    if fixture_id == "insufficient_context" and not validate_clear_resolved_predecessor(evidence=predecessor_evidence):
        raise ValueError("predecessor_not_authorized")
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=fixture["selected_moves"], battle_input=fixture["battle_input"], move_repository=fixture["move_repository"],
    )
    request = prepared.get("recommendation_request")
    return {
        "fixture_id": fixture_id, "preparation_status": prepared.get("status"),
        "provider_eligible": prepared.get("status") == "ready" and isinstance(request, Mapping),
        "failure_codes": list(prepared.get("errors", [])),
    }


def execute_single_authorized_fixture(
    *,
    fixture_id: str,
    completed_fixture_ids: Sequence[str],
    actual_provider_approved: bool,
    provider_evaluation_state: str,
    provider_factory: Callable[[], Callable[..., tuple[Mapping[str, Any], Mapping[str, Any]]]],
    model: str,
    predecessor_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one injected provider call only after every single-fixture guard passes."""
    fixture = _single_authorized_fixture(fixture_id=fixture_id, completed_fixture_ids=completed_fixture_ids)
    if fixture_id == "insufficient_context" and not validate_clear_resolved_predecessor(evidence=predecessor_evidence):
        raise ValueError("predecessor_not_authorized")
    if not actual_provider_approved or provider_evaluation_state != "ACTIVE":
        return suspended_fixture_report(fixture_id=fixture_id)
    if not callable(provider_factory) or not isinstance(model, str) or not model:
        raise ValueError("invalid_authorized_runner_configuration")
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=fixture["selected_moves"], battle_input=fixture["battle_input"], move_repository=fixture["move_repository"],
    )
    request = prepared.get("recommendation_request")
    provider_eligible = prepared.get("status") == "ready" and isinstance(request, Mapping)
    result: dict[str, Any] = {
        "fixture_id": fixture_id, "preparation_status": prepared.get("status"), "provider_eligible": provider_eligible,
        "provider_invoked": False, "completion_status": None, "presentation_status": None,
        "recommended_move": None, "recommended_slot_index": None, "failure_codes": list(prepared.get("errors", [])),
        "usage": {}, "evidence_preserved": isinstance(prepared.get("evidence_bundle"), Mapping), "actual_call_count": 0,
        "remaining_call_budget": REMAINING_AUTHORIZED_CALL_BUDGET,
    }
    if not provider_eligible:
        result["completion_status"] = "blocked"
        return result
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    if payload.get("status"):
        result["completion_status"] = payload["status"]
        result["failure_codes"] = list(payload.get("errors", []))
        return result
    provider_call = provider_factory()
    if not callable(provider_call):
        raise ValueError("invalid_provider_factory")
    result["provider_invoked"] = True
    result["actual_call_count"] = 1
    result["remaining_call_budget"] = REMAINING_AUTHORIZED_CALL_BUDGET - 1
    try:
        decoded, usage = provider_call(provider_payload=payload, model=model)
    except Exception as error:
        code = getattr(error, "code", "provider_unavailable")
        code = code if isinstance(code, str) and code in _SANITIZED_PROVIDER_FAILURES else "provider_unavailable"
        result["completion_status"] = "timeout_uncertain" if code == "provider_timeout" else code
        result["failure_codes"] = [code]
        return result
    result["usage"] = _sanitized_usage(usage)
    adapted = adapt_provider_recommendation_response(provider_response=decoded)
    if adapted.get("status") == "provider_response_validation_failed":
        result["completion_status"] = "provider_response_validation_failed"
        result["failure_codes"] = list(adapted.get("errors", []))
        return result
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=adapted)
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    recommendation = completed.get("recommendation_result") if isinstance(completed.get("recommendation_result"), Mapping) else {}
    result.update(
        completion_status=completed.get("status"), presentation_status=presentation.get("status"),
        recommended_move=recommendation.get("recommended_move") if completed.get("status") == "resolved" else None,
        recommended_slot_index=recommendation.get("recommended_slot_index") if completed.get("status") == "resolved" else None,
        failure_codes=list(completed.get("errors", [])), evidence_preserved=isinstance(completed.get("evidence_bundle"), Mapping),
    )
    return result


def aggregate_authorized_fixture_results(*, results: Sequence[Mapping[str, Any]], actual_call_count: int) -> dict[str, Any]:
    """Aggregate only sanitized actual-evaluation fields; no reliability inference."""
    failures: dict[str, int] = {}
    for result in results:
        for code in result.get("failure_codes", []):
            if isinstance(code, str):
                failures[code] = failures.get(code, 0) + 1
    return {
        "fixture_count": len(results), "provider_eligible_count": sum(bool(result.get("provider_eligible")) for result in results),
        "provider_blocked_count": sum(not bool(result.get("provider_eligible")) for result in results),
        "provider_invoked_count": sum(bool(result.get("provider_invoked")) for result in results),
        "actual_call_count": actual_call_count,
        "decoded_success_count": sum(result.get("decoded_status") in _RECOMMENDATION_STATUSES for result in results),
        "completion_success_count": sum(result.get("completion_status") in _RECOMMENDATION_STATUSES for result in results),
        "presentation_count": sum(bool(result.get("presentation_produced")) for result in results),
        "failure_distribution": failures,
    }
