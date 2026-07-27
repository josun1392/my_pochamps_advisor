"""Pure v14.1 design contracts; no evaluation or provider orchestration."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from copy import deepcopy
import math

from llm.advisor_battle_state_context import build_deterministic_calculation_context
from llm.advisor_turn_snapshot import (
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
    build_snapshot_trusted_level_provenance,
    build_request_start_recommendation_snapshot,
    snapshot_deterministic_context,
)
from llm.advisor_q12_snapshot_adapter import invoke_existing_q12_from_snapshot

CANDIDATE_STATUSES = frozenset({"resolved", "partial", "unavailable"})
RECOMMENDATION_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate", "validation_failed"})

def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    required = {"move", "status", "availability", "self_effects", "dynamic_move", "warnings", "unavailable_reasons"}
    if not required <= set(candidate) or not isinstance(candidate.get("move"), str) or candidate.get("status") not in CANDIDATE_STATUSES:
        raise ValueError("invalid candidate schema")
    if not all(isinstance(candidate[key], list) for key in ("self_effects", "warnings", "unavailable_reasons")):
        raise ValueError("invalid candidate collections")
    return deepcopy(dict(candidate))

def build_evidence_bundle(snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], limitations: Sequence[str]) -> dict[str, Any]:
    normalized = [validate_candidate(candidate) for candidate in candidates]
    return {"battle_snapshot_summary": deepcopy(dict(snapshot)), "candidates": normalized, "comparison_policy": {"allow_partial_candidates": True, "no_untrusted_inference": True, "preserve_slot_order": True}, "known_limitations": list(limitations)}

def validate_recommendation(response: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status = response.get("recommendation_status")
    if status not in RECOMMENDATION_STATUSES: raise ValueError("invalid recommendation status")
    moves = {candidate["move"] for candidate in candidates}
    move = response.get("recommended_move")
    if status == "resolved" and (not isinstance(move, str) or move not in moves): raise ValueError("recommendation outside candidate exact-set")
    if any(key not in response or not isinstance(response[key], list) for key in ("primary_reasons", "risks", "alternatives")): raise ValueError("invalid recommendation evidence")
    return dict(response)

def _metadata_value(metadata: Any, name: str) -> Any:
    return metadata.get(name) if isinstance(metadata, Mapping) else getattr(metadata, name, None)


def _selected_move_from_metadata(move: str, metadata: Any) -> dict[str, Any]:
    fields = ("category", "power", "type", "accuracy", "drain", "min_hits", "max_hits", "healing")
    selected = {"move_id": _metadata_value(metadata, "move_id") or move}
    selected.update({field: _metadata_value(metadata, field) for field in fields if _metadata_value(metadata, field) is not None})
    return selected


def _dynamic_summary(context: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(context, Mapping):
        return None
    key = next((name for name in context if isinstance(name, str) and name.endswith("_power_assessment") or name == "environment_based_move_assessment"), None)
    if key is None or not isinstance(context.get(key), Mapping):
        return None
    assessment = context[key]
    family = key.removesuffix("_assessment")
    resolved = assessment.get("status") == "resolved"
    return {
        "family": family,
        "assessment_key": key,
        "status": assessment.get("status", "unavailable"),
        "effective_power": assessment.get("effective_power") if resolved else None,
        "effective_type": assessment.get("effective_type") if resolved and family == "environment_based_move" else None,
    }


def _damage_summary(context: Mapping[str, Any] | None) -> dict[str, Any]:
    estimates = context.get("damage_estimates") if isinstance(context, Mapping) else None
    estimate = estimates[0] if isinstance(estimates, list) and estimates and isinstance(estimates[0], Mapping) else None
    if not isinstance(estimate, Mapping) or estimate.get("calculation_status") != "resolved":
        reason = estimate.get("reason") if isinstance(estimate, Mapping) and isinstance(estimate.get("reason"), str) else "deterministic_damage_unavailable"
        return {"status": "unavailable", "reason": reason}
    summary = {"status": "resolved", "minimum": estimate["min_damage"], "maximum": estimate["max_damage"]}
    hp = context.get("hp_assessments") if isinstance(context, Mapping) else None
    if isinstance(hp, list) and hp and isinstance(hp[0], Mapping) and isinstance(hp[0].get("two_hit_ko"), Mapping):
        summary["ko"] = hp[0]["two_hit_ko"].get("status")
    return summary


def _optional_outputs(context: Mapping[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if not isinstance(context, Mapping):
        return {}, [], []
    outputs: dict[str, Any] = {}
    reasons: list[str] = []
    for source, target, fields in (
        ("hit_chance_assessment", "hit_chance", ("hit_chance_percent", "result", "reason")),
        ("move_order_assessment", "move_order", ("result", "reason")),
    ):
        assessment = context.get(source)
        if isinstance(assessment, Mapping):
            status = assessment.get("calculation_status", assessment.get("status", "unavailable"))
            outputs[target] = {"status": status, **{field: assessment[field] for field in fields if field in assessment}}
            if status == "unavailable" and isinstance(assessment.get("reason"), str):
                reasons.append(assessment["reason"])
    self_effects = []
    for source in ("direct_healing_assessment", "drain_recoil_assessment", "self_consequence_assessment"):
        assessment = context.get(source)
        if isinstance(assessment, Mapping):
            status = assessment.get("calculation_status", assessment.get("status", "unavailable"))
            self_effects.append({"kind": source.removesuffix("_assessment"), "status": status, **{key: deepcopy(assessment[key]) for key in ("effect", "reason") if key in assessment}})
            if status == "unavailable" and isinstance(assessment.get("reason"), str):
                reasons.append(assessment["reason"])
    return outputs, self_effects, reasons


def _production_context(snapshot: Mapping[str, Any], selected_move: Mapping[str, Any]) -> dict[str, Any] | None:
    # Legacy deterministic helpers predate canonical provenance fields.  Feed
    # them a detached value-only view while Q12 continues to consume the frozen
    # provenance-aware snapshot separately.
    context = _without_internal_provenance(snapshot)
    return build_deterministic_calculation_context(
        context.get("final_stat_context"), context.get("stat_stage_context"), selected_move,
        context.get("current_hp_context"), context.get("pokemon"), context.get("condition_context"),
        context.get("field_state_context"), context.get("battle_format_context"), context.get("opponent_selected_move"),
        context.get("attacker_level_context"), context.get("observed_previous_damage_context"),
        context.get("battle_counter_context"), context.get("consecutive_use_context"),
        context.get("weight_context"), context.get("turn_event_context"),
    )


def _without_internal_provenance(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _without_internal_provenance(item) for key, item in value.items() if key != "provenance"}
    if isinstance(value, list):
        return [_without_internal_provenance(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_without_internal_provenance(item) for item in value)
    return deepcopy(value)


def evaluate_move_candidate(*, slot_index: int, move: Any, battle_snapshot: Mapping[str, Any], repositories: Any, turn_snapshot: Any = None, selectable_moves: Sequence[str | None] | None = None, species_repository: Any = None) -> dict[str, Any]:
    """Pure v14.2 slot evaluator; isolates metadata failures per candidate."""
    if not isinstance(slot_index, int) or not 0 <= slot_index < 4: raise ValueError("invalid slot index")
    if not isinstance(move, str) or not move:
        return {"slot_index":slot_index,"move":"unknown","status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["invalid_move_identity"]}
    try:
        metadata = repositories.get(move) if hasattr(repositories, "get") else repositories[move]
    except Exception:
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["move_metadata_unavailable"]}
    if not isinstance(metadata, Mapping) and not hasattr(metadata, "category"):
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["move_metadata_unavailable"]}
    if _metadata_value(metadata, "category") == "status":
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":{"status":"not_applicable"},"q12_damage":{"status":"unavailable","limitations":["status_move_not_damaging"]},"self_effects":[],"dynamic_move":None,"warnings":["unsupported_non_damage_utility_ranking"],"unavailable_reasons":[]}
    snapshot = battle_snapshot if isinstance(battle_snapshot, Mapping) else {}
    selected_move = _selected_move_from_metadata(move, metadata)
    if turn_snapshot is not None:
        try:
            damage_input = build_snapshot_damage_input(
                turn_snapshot,
                candidate_slot_index=slot_index,
                candidate_move_id=move,
                selectable_moves=selectable_moves or (),
                move_metadata=selected_move,
            )
        except ValueError:
            return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["invalid_snapshot"]}
        selected_move = deepcopy(damage_input["move"])
        q12_damage = _snapshot_q12_damage(
            turn_snapshot=turn_snapshot, damage_input=damage_input,
            species_repository=species_repository,
        )
    else:
        q12_damage = {"status": "unavailable", "limitations": ["snapshot_q12_unavailable"]}
    context = _production_context(snapshot, selected_move)
    dynamic_move = _dynamic_summary(context)
    damage = _damage_summary(context)
    optional_outputs, self_effects, optional_reasons = _optional_outputs(context)
    if dynamic_move is not None and dynamic_move["status"] != "resolved":
        reasons = ["required_dynamic_context_unavailable"]
        assessment = context.get(dynamic_move["assessment_key"]) if isinstance(context, Mapping) else None
        if isinstance(assessment, Mapping) and isinstance(assessment.get("reason"), str): reasons.append(assessment["reason"])
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","damage":damage,"q12_damage":q12_damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":reasons,**optional_outputs}
    if damage["status"] != "resolved":
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":damage,"q12_damage":q12_damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":[damage["reason"], *optional_reasons],**optional_outputs}
    if optional_reasons:
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":damage,"q12_damage":q12_damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":optional_reasons,**optional_outputs}
    return {"slot_index":slot_index,"move":move,"status":"resolved","availability":"usable","damage":damage,"q12_damage":q12_damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":[],**optional_outputs}

def _snapshot_q12_damage(*, turn_snapshot: Any, damage_input: Mapping[str, Any], species_repository: Any) -> dict[str, Any]:
    if species_repository is None:
        return {"status": "unavailable", "limitations": ["species_repository_unavailable"]}
    try:
        provenance = build_snapshot_stat_provenance(turn_snapshot, species_repository=species_repository)
        level = build_snapshot_trusted_level_provenance(turn_snapshot)
        if level.get("available") is not True:
            return {"status": "unavailable", "limitations": [str(level.get("reason", "trusted_level_unavailable"))]}
        return invoke_existing_q12_from_snapshot(
            damage_input, stat_provenance=provenance, trusted_level=level.get("value"),
        )
    except (TypeError, ValueError):
        return {"status": "unavailable", "limitations": ["invalid_snapshot"]}


def evaluate_move_slots(*, moves: Sequence[Any], battle_snapshot: Mapping[str, Any], repositories: Any, maximum_slots: int = 4, turn_snapshot: Any = None, species_repository: Any = None) -> list[dict[str, Any]]:
    if isinstance(moves, (str, bytes)) or not isinstance(moves, Sequence) or len(moves) > maximum_slots: raise ValueError("invalid move slots")
    return [evaluate_move_candidate(slot_index=index, move=move, battle_snapshot=deepcopy(dict(battle_snapshot)), repositories=repositories, turn_snapshot=turn_snapshot, selectable_moves=moves, species_repository=species_repository) for index, move in enumerate(moves) if move is not None]

_RECOMMENDATION_GUARDRAILS = {
    "select_only_from_selectable_exact_set": True,
    "do_not_modify_deterministic_evidence": True,
    "do_not_infer_opponent_moves": True,
    "do_not_infer_items_abilities_or_stats": True,
    "do_not_claim_unsupported_mechanics": True,
}
_REQUEST_READINESS = frozenset({"ready", "no_candidates", "no_selectable_candidates", "invalid_evidence_bundle"})


def _candidate_eligibility(candidate: Mapping[str, Any]) -> str:
    status, availability = candidate.get("status"), candidate.get("availability")
    if status == "resolved" and availability == "usable":
        return "eligible"
    if status == "partial" and availability in {"usable", "partially_evaluable"}:
        return "eligible_with_warnings"
    if status == "unavailable" and availability == "unavailable":
        return "not_selectable"
    raise ValueError("invalid candidate eligibility")


def _exact_pair(value: Any, *, exact: bool = True) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not {"slot_index", "move"} <= set(value) or (exact and set(value) != {"slot_index", "move"}):
        raise ValueError("invalid exact-set entry")
    if not isinstance(value["slot_index"], int) or isinstance(value["slot_index"], bool) or not 0 <= value["slot_index"] < 4:
        raise ValueError("invalid exact-set entry")
    if not isinstance(value["move"], str) or not value["move"]:
        raise ValueError("invalid exact-set entry")
    return {"slot_index": value["slot_index"], "move": value["move"]}


def _invalid_request() -> dict[str, Any]:
    request = {
        "request_version": "v14.3",
        "readiness": {"status": "invalid_evidence_bundle", "selectable_candidate_count": 0},
        "battle_snapshot_summary": {}, "candidate_exact_set": [],
        "selectable_candidate_exact_set": [], "candidate_comparisons": [],
        "known_limitations": [], "guardrails": deepcopy(_RECOMMENDATION_GUARDRAILS),
    }
    return request


def _validate_request_contract(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping) or request.get("request_version") != "v14.3":
        raise ValueError("invalid recommendation request")
    readiness = request.get("readiness")
    if not isinstance(readiness, Mapping) or readiness.get("status") not in _REQUEST_READINESS:
        raise ValueError("invalid recommendation request")
    if request.get("guardrails") != _RECOMMENDATION_GUARDRAILS:
        raise ValueError("invalid recommendation request")
    candidate_set, selectable_set, comparisons = request.get("candidate_exact_set"), request.get("selectable_candidate_exact_set"), request.get("candidate_comparisons")
    if not isinstance(candidate_set, list) or not isinstance(selectable_set, list) or not isinstance(comparisons, list):
        raise ValueError("invalid recommendation request")
    pairs = [_exact_pair(value) for value in candidate_set]
    if len({pair["slot_index"] for pair in pairs}) != len(pairs):
        raise ValueError("invalid recommendation request")
    selectable = [_exact_pair(value) for value in selectable_set]
    if any(pair not in pairs for pair in selectable) or len({pair["slot_index"] for pair in selectable}) != len(selectable):
        raise ValueError("invalid recommendation request")
    if len(comparisons) != len(pairs):
        raise ValueError("invalid recommendation request")
    expected_selectable = []
    for pair, row in zip(pairs, comparisons, strict=True):
        if not isinstance(row, Mapping) or _exact_pair(row, exact=False) != pair:
            raise ValueError("invalid recommendation request")
        eligibility = _candidate_eligibility(row)
        if row.get("eligibility") != eligibility:
            raise ValueError("invalid recommendation request")
        if eligibility != "not_selectable":
            expected_selectable.append(pair)
    if selectable != expected_selectable:
        raise ValueError("invalid recommendation request")
    expected_status = "no_candidates" if not pairs else "ready" if selectable else "no_selectable_candidates"
    if readiness.get("status") != expected_status or readiness.get("selectable_candidate_count") != len(selectable):
        raise ValueError("invalid recommendation request")


def build_recommendation_request(*, evidence_bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence_bundle, Mapping):
        return _invalid_request()
    candidates = evidence_bundle.get("candidates")
    limitations = evidence_bundle.get("known_limitations")
    snapshot = evidence_bundle.get("battle_snapshot_summary")
    if not isinstance(candidates, list) or not isinstance(limitations, list) or not isinstance(snapshot, Mapping):
        return _invalid_request()
    try:
        comparisons = []
        pairs = []
        for candidate in candidates:
            normalized = validate_candidate(candidate)
            pair = _exact_pair(normalized, exact=False)
            if pair["slot_index"] in {existing["slot_index"] for existing in pairs}:
                raise ValueError("duplicate slot index")
            eligibility = _candidate_eligibility(normalized)
            # Q12 is internal deterministic evidence.  Keep its compact result
            # on the prepared candidate while preserving the provider comparison
            # contract and never serializing a calculation input/provenance block.
            provider_candidate = {key: value for key, value in normalized.items() if key != "q12_damage"}
            comparisons.append({**deepcopy(provider_candidate), "eligibility": eligibility})
            pairs.append(pair)
        if not all(isinstance(item, str) for item in limitations):
            raise ValueError("invalid known limitations")
    except (TypeError, ValueError):
        return _invalid_request()
    selectable = [deepcopy(pair) for pair, row in zip(pairs, comparisons, strict=True) if row["eligibility"] != "not_selectable"]
    readiness = "no_candidates" if not pairs else "ready" if selectable else "no_selectable_candidates"
    request = {
        "request_version": "v14.3",
        "readiness": {"status": readiness, "selectable_candidate_count": len(selectable)},
        "battle_snapshot_summary": deepcopy(dict(snapshot)),
        "candidate_exact_set": deepcopy(pairs),
        "selectable_candidate_exact_set": selectable,
        "candidate_comparisons": comparisons,
        "known_limitations": deepcopy(limitations),
        "guardrails": deepcopy(_RECOMMENDATION_GUARDRAILS),
    }
    turn_snapshot = snapshot.get("turn_snapshot") if isinstance(snapshot, Mapping) else None
    current_state = turn_snapshot.get("current_state") if isinstance(turn_snapshot, Mapping) else None
    runtime = current_state.get("runtime_advice_state") if isinstance(current_state, Mapping) else None
    if isinstance(runtime, Mapping):
        request["runtime_advice_state"] = deepcopy(dict(runtime))
    return request


def validate_recommendation_selection(*, request: Mapping[str, Any], recommended_move: str, recommended_slot_index: int) -> dict[str, Any]:
    _validate_request_contract(request)
    if request["readiness"]["status"] != "ready":
        raise ValueError("request not ready")
    pair = {"move": recommended_move, "slot_index": recommended_slot_index}
    if pair not in request["selectable_candidate_exact_set"]:
        raise ValueError("selection outside selectable exact-set")
    return deepcopy(pair)


def serialize_recommendation_request(request: Mapping[str, Any]) -> dict[str, Any]:
    banned = {"apikey", "token", "accesstoken", "refreshtoken", "authorization", "credential", "credentials", "providersecret", "clientsecret", "rawresponse", "rawproviderresponse", "traceback", "stacktrace"}

    def clean(value: Any) -> Any:
        if type(value) is dict:
            result = {}
            for key, item in value.items():
                if type(key) is not str or key.lower().replace("_", "").replace("-", "") in banned:
                    raise ValueError("unsafe request field")
                result[key] = clean(item)
            return result
        if type(value) is list:
            return [clean(item) for item in value]
        if type(value) is float:
            if not math.isfinite(value):
                raise ValueError("non-json-safe value")
            return value
        if value is None or type(value) in {str, int, bool}:
            return value
        raise ValueError("non-json-safe value")

    return clean(request)


_RESPONSE_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate", "validation_failed"})
_CLAIM_KINDS = frozenset({"damage", "ko", "hit_chance", "move_order", "self_effect", "dynamic_mechanic", "partial_context"})
_FORBIDDEN_RESPONSE_KEYS = frozenset({
    "rawresponse", "rawproviderresponse", "traceback", "stacktrace", "apikey", "token", "authorization",
    "credential", "credentials", "providersecret", "clientsecret", "accesstoken", "refreshtoken", "rawprompt",
    "providermodel", "modeloverride", "network", "networkconfiguration", "deterministicevidence", "damagerange",
    "candidatecomparisons", "unknownmove", "opponentmove", "item", "ability", "ev", "iv",
})


def _response_failure(code: str) -> dict[str, Any]:
    return {"status": "validation_failed", "recommended_move": None, "recommended_slot_index": None,
            "primary_reasons": [], "risks": [], "alternatives": [], "errors": [code]}


def _has_forbidden_response_content(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if normalized in _FORBIDDEN_RESPONSE_KEYS or _has_forbidden_response_content(item):
                return True
    elif isinstance(value, list):
        return any(_has_forbidden_response_content(item) for item in value)
    return False


def _comparison_for_pair(request: Mapping[str, Any], pair: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for comparison in request.get("candidate_comparisons", []):
        if isinstance(comparison, Mapping) and comparison.get("move") == pair["move"] and comparison.get("slot_index") == pair["slot_index"]:
            return comparison
    return None


def _validate_claim(reason: Any, candidate: Mapping[str, Any]) -> None:
    if not isinstance(reason, Mapping) or set(reason) != {"kind", "claim"} or reason.get("kind") not in _CLAIM_KINDS or not isinstance(reason.get("claim"), str) or not reason["claim"]:
        raise ValueError("invalid_claim")
    kind = reason["kind"]
    damage = candidate.get("damage")
    if kind == "damage" and (not isinstance(damage, Mapping) or damage.get("status") != "resolved"):
        raise ValueError("claim_evidence_unavailable")
    if kind == "ko" and (not isinstance(damage, Mapping) or "ko" not in damage or damage["ko"] is None):
        raise ValueError("claim_evidence_unavailable")
    if kind == "hit_chance" and not isinstance(candidate.get("hit_chance"), Mapping):
        raise ValueError("claim_evidence_unavailable")
    if kind == "move_order" and not isinstance(candidate.get("move_order"), Mapping):
        raise ValueError("claim_evidence_unavailable")
    if kind == "dynamic_mechanic" and not isinstance(candidate.get("dynamic_move"), Mapping):
        raise ValueError("claim_evidence_unavailable")
    if kind == "self_effect" and (not isinstance(candidate.get("self_effects"), list) or not candidate["self_effects"]):
        raise ValueError("claim_evidence_unavailable")
    if kind == "partial_context" and candidate.get("status") == "resolved" and any(word in reason["claim"].lower() for word in ("missing", "unavailable", "incomplete")):
        raise ValueError("claim_evidence_contradiction")


def parse_recommendation_response(*, request: Mapping[str, Any], response_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an already-decoded, offline recommendation response without provider access."""
    if not isinstance(response_payload, Mapping):
        return _response_failure("invalid_response_payload")
    if _has_forbidden_response_content(response_payload):
        return _response_failure("forbidden_response_content")
    status = response_payload.get("recommendation_status")
    if status not in _RESPONSE_STATUSES or status == "validation_failed":
        return _response_failure("unsupported_recommendation_status")
    reasons, risks, alternatives = response_payload.get("primary_reasons"), response_payload.get("risks"), response_payload.get("alternatives")
    if not isinstance(reasons, list) or not isinstance(risks, list) or not isinstance(alternatives, list):
        return _response_failure("invalid_response_collections")
    move, slot = response_payload.get("recommended_move"), response_payload.get("recommended_slot_index")
    if status == "resolved":
        if not isinstance(move, str) or not isinstance(slot, int) or isinstance(slot, bool):
            return _response_failure("missing_recommended_candidate")
        try:
            validate_recommendation_selection(request=request, recommended_move=move, recommended_slot_index=slot)
        except ValueError:
            return _response_failure("recommended_candidate_not_selectable")
        primary = {"move": move, "slot_index": slot}
        candidate = _comparison_for_pair(request, primary)
        if candidate is None:
            return _response_failure("request_candidate_evidence_missing")
    else:
        if move is not None or slot is not None:
            return _response_failure("unexpected_recommended_candidate")
        readiness = request.get("readiness", {}).get("status") if isinstance(request, Mapping) else None
        if status == "no_usable_candidate" and readiness not in {"no_selectable_candidates", "no_candidates"}:
            return _response_failure("request_not_no_usable_candidate")
        if status == "insufficient_context":
            candidate = {}
        else:
            candidate = {}
        primary = None
    try:
        for reason in [*reasons, *risks]:
            _validate_claim(reason, candidate)
        seen_alternatives = set()
        for alternative in alternatives:
            if not isinstance(alternative, Mapping) or set(alternative) != {"move", "slot_index", "reason"}:
                raise ValueError("invalid_alternative")
            pair = {"move": alternative.get("move"), "slot_index": alternative.get("slot_index")}
            validate_recommendation_selection(request=request, recommended_move=pair["move"], recommended_slot_index=pair["slot_index"])
            key = (pair["move"], pair["slot_index"])
            if key in seen_alternatives or pair == primary:
                raise ValueError("invalid_alternative")
            alternative_candidate = _comparison_for_pair(request, pair)
            if alternative_candidate is None:
                raise ValueError("invalid_alternative")
            _validate_claim(alternative["reason"], alternative_candidate)
            seen_alternatives.add(key)
    except ValueError as error:
        return _response_failure(str(error))
    return {"status": status, "recommended_move": move, "recommended_slot_index": slot,
            "primary_reasons": deepcopy(reasons), "risks": deepcopy(risks),
            "alternatives": deepcopy(alternatives), "errors": []}


def _cycle_result(*, status: str, candidates: Sequence[Mapping[str, Any]] = (), evidence_bundle: Mapping[str, Any] | None = None, recommendation_request: Mapping[str, Any] | None = None, recommendation_result: Mapping[str, Any] | None = None, errors: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "status": status,
        "candidates": deepcopy(list(candidates)),
        "evidence_bundle": deepcopy(dict(evidence_bundle)) if isinstance(evidence_bundle, Mapping) else None,
        "recommendation_request": deepcopy(dict(recommendation_request)) if isinstance(recommendation_request, Mapping) else None,
        "recommendation_result": deepcopy(dict(recommendation_result)) if isinstance(recommendation_result, Mapping) else None,
        "errors": list(errors),
    }


def prepare_recommendation_cycle(*, moves: Sequence[Any], battle_snapshot: Mapping[str, Any], repositories: Any, battle_snapshot_summary: Mapping[str, Any] | None = None, known_limitations: Sequence[str] = (), turn_snapshot: Any = None, species_repository: Any = None) -> dict[str, Any]:
    """Prepare a provider-neutral recommendation cycle from deterministic evidence."""
    if isinstance(moves, (str, bytes)) or not isinstance(moves, Sequence):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_move_slots"])
    if not isinstance(battle_snapshot, Mapping) or (battle_snapshot_summary is not None and not isinstance(battle_snapshot_summary, Mapping)):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_battle_snapshot"])
    if isinstance(known_limitations, (str, bytes)) or not isinstance(known_limitations, Sequence) or not all(isinstance(item, str) for item in known_limitations):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_battle_snapshot"])
    try:
        candidates = evaluate_move_slots(moves=moves, battle_snapshot=battle_snapshot, repositories=repositories, turn_snapshot=turn_snapshot, species_repository=species_repository)
    except (TypeError, ValueError):
        return _cycle_result(status="invalid_snapshot", errors=["invalid_move_slots"])
    except Exception:
        return _cycle_result(status="candidate_evaluation_failed", errors=["candidate_evaluation_failed"])
    summary = battle_snapshot if battle_snapshot_summary is None else battle_snapshot_summary
    try:
        evidence = build_evidence_bundle(summary, candidates, known_limitations)
    except (TypeError, ValueError):
        return _cycle_result(status="request_validation_failed", candidates=candidates, errors=["request_validation_failed"])
    if not candidates:
        return _cycle_result(status="no_candidates", candidates=candidates, evidence_bundle=evidence, errors=["no_candidates"])
    request = build_recommendation_request(evidence_bundle=evidence)
    readiness = request.get("readiness", {}).get("status") if isinstance(request, Mapping) else None
    if readiness == "invalid_evidence_bundle":
        return _cycle_result(status="request_validation_failed", candidates=candidates, evidence_bundle=evidence, errors=["request_validation_failed"])
    if readiness == "no_selectable_candidates":
        return _cycle_result(status="no_selectable_candidates", candidates=candidates, evidence_bundle=evidence, errors=["no_selectable_candidates"])
    if readiness != "ready":
        return _cycle_result(status="request_validation_failed", candidates=candidates, evidence_bundle=evidence, errors=["request_validation_failed"])
    return _cycle_result(status="ready", candidates=candidates, evidence_bundle=evidence, recommendation_request=request)


def complete_recommendation_cycle(*, prepared_cycle: Mapping[str, Any], response_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Complete a ready provider-neutral cycle through the offline parser only."""
    if not isinstance(prepared_cycle, Mapping) or prepared_cycle.get("status") != "ready" or not isinstance(prepared_cycle.get("recommendation_request"), Mapping):
        source = prepared_cycle if isinstance(prepared_cycle, Mapping) else {}
        return _cycle_result(status="cycle_not_ready", candidates=source.get("candidates", ()), evidence_bundle=source.get("evidence_bundle"), errors=["cycle_not_ready"])
    candidates = prepared_cycle.get("candidates", ())
    evidence = prepared_cycle.get("evidence_bundle")
    request = prepared_cycle["recommendation_request"]
    if _RUNTIME_PROVIDER_KEY in request and "grounding" not in response_payload:
        return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=["grounding_required"])
    if _RUNTIME_PROVIDER_KEY in request:
        errors = validate_runtime_grounding(runtime_advice_state=request[_RUNTIME_PROVIDER_KEY], grounding=response_payload.get("grounding"), legacy_compatible=False)
        if errors:
            return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=errors)
    result = parse_recommendation_response(request=request, response_payload=response_payload)
    if result["status"] == "validation_failed":
        return _cycle_result(status="response_validation_failed", candidates=candidates, evidence_bundle=evidence, recommendation_request=request, errors=result.get("errors", ["response_validation_failed"]))
    return _cycle_result(status=result["status"], candidates=candidates, evidence_bundle=evidence, recommendation_request=request, recommendation_result=result)


_UI_SNAPSHOT_CONTEXT_KEYS = (
    "final_stat_context", "stat_stage_context", "current_hp_context", "condition_context", "field_state_context",
    "battle_format_context", "attacker_level_context", "observed_previous_damage_context", "battle_counter_context",
    "consecutive_use_context", "weight_context", "turn_event_context",
)
_UI_RECOMMENDATION_LIMITATION_GUARDRAILS = (
    "Unknown opponent moves remain untrusted.", "Unknown item, ability, EV, IV, nature, and final stats remain untrusted unless confirmed.",
    "No multi-turn planning, switch recommendation, Turn Engine, or untrusted inference.",
)


def adapt_ui_move_slots(*, selected_moves: Sequence[Any]) -> tuple[str | None, ...]:
    """Normalize current UI move slots without reducing them to the selected index."""
    if isinstance(selected_moves, (str, bytes)) or not isinstance(selected_moves, Sequence) or len(selected_moves) > 4:
        raise ValueError("invalid_move_slots")
    result = []
    for value in selected_moves:
        if value is None:
            result.append(None)
            continue
        move_id = value.get("move_id") if isinstance(value, Mapping) else getattr(value, "move_id", None)
        if not isinstance(move_id, str) or not move_id:
            raise ValueError("unsupported_move_slot_shape")
        result.append(move_id)
    return tuple(result)


def adapt_ui_battle_snapshot(*, battle_input: Mapping[str, Any]) -> dict[str, Any]:
    """Copy only trusted deterministic contexts from normalized UI battle input."""
    if not isinstance(battle_input, Mapping):
        raise ValueError("invalid_battle_snapshot")
    pokemon = battle_input.get("pokemon")
    if not isinstance(pokemon, Mapping) or not isinstance(pokemon.get("my_active"), Mapping) or not isinstance(pokemon.get("opponent_active"), Mapping):
        raise ValueError("missing_selected_pokemon")
    snapshot = {"pokemon": deepcopy(dict(pokemon))}
    for key in _UI_SNAPSHOT_CONTEXT_KEYS:
        if isinstance(battle_input.get(key), Mapping):
            snapshot[key] = deepcopy(dict(battle_input[key]))
    moves = battle_input.get("moves")
    if isinstance(moves, Mapping) and isinstance(moves.get("opponent_selected_move"), Mapping):
        snapshot["opponent_selected_move"] = deepcopy(dict(moves["opponent_selected_move"]))
    elif isinstance(battle_input.get("opponent_selected_move"), Mapping):
        snapshot["opponent_selected_move"] = deepcopy(dict(battle_input["opponent_selected_move"]))
    return snapshot


def build_ui_recommendation_snapshot_summary(*, battle_input: Mapping[str, Any], turn_snapshot: Any = None) -> dict[str, Any]:
    if not isinstance(battle_input, Mapping):
        raise ValueError("invalid_battle_snapshot")
    scenario = battle_input.get("scenario")
    summary = {}
    if isinstance(scenario, Mapping):
        summary["scenario"] = {key: deepcopy(scenario[key]) for key in ("mode", "format_note") if key in scenario}
    pokemon = battle_input.get("pokemon")
    if isinstance(pokemon, Mapping):
        summary["pokemon"] = deepcopy(dict(pokemon))
    if turn_snapshot is not None:
        summary["turn_snapshot"] = deepcopy(turn_snapshot.to_dict())
    return summary


def _ui_known_limitations(battle_input: Mapping[str, Any]) -> list[str]:
    scenario = battle_input.get("scenario") if isinstance(battle_input, Mapping) else None
    existing = scenario.get("known_limitations") if isinstance(scenario, Mapping) else None
    values = [item for item in existing if isinstance(item, str)] if isinstance(existing, list) else []
    return list(dict.fromkeys([*values, *_UI_RECOMMENDATION_LIMITATION_GUARDRAILS]))


def prepare_ui_recommendation_cycle(*, selected_moves: Sequence[Any], battle_input: Mapping[str, Any], move_repository: Any, species_repository: Any = None, observation_snapshot: Mapping[str, Any] | None = None, trusted_turn_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Prepare an offline recommendation cycle from UI-shaped, trusted inputs."""
    try:
        moves = adapt_ui_move_slots(selected_moves=selected_moves)
        request_turn_snapshot = build_request_start_recommendation_snapshot(
            battle_input, selectable_moves=moves, observation_snapshot=observation_snapshot, trusted_turn_context=trusted_turn_context
        )
        snapshot = adapt_ui_battle_snapshot(battle_input=battle_input)
        snapshot.update(snapshot_deterministic_context(request_turn_snapshot))
        summary = build_ui_recommendation_snapshot_summary(
            battle_input=battle_input, turn_snapshot=request_turn_snapshot
        )
    except ValueError as error:
        return _cycle_result(status="invalid_snapshot", errors=[str(error)])
    return prepare_recommendation_cycle(
        moves=moves, battle_snapshot=snapshot, repositories=move_repository,
        battle_snapshot_summary=summary, known_limitations=_ui_known_limitations(battle_input),
        turn_snapshot=request_turn_snapshot, species_repository=species_repository,
    )


_PROVIDER_OUTBOUND_KEYS = (
    "request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set",
    "candidate_comparisons", "known_limitations", "guardrails",
)
_RUNTIME_PROVIDER_KEY = "runtime_advice_state"
_PROVIDER_RESPONSE_KEYS = (
    "recommendation_status", "recommended_move", "recommended_slot_index", "primary_reasons", "risks", "alternatives",
)
_GROUNDED_PROVIDER_RESPONSE_KEYS = (*_PROVIDER_RESPONSE_KEYS, "grounding")
_PROVIDER_RESPONSE_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate"})
_PREPARED_CYCLE_KEYS = frozenset({"status", "candidates", "evidence_bundle", "recommendation_request", "recommendation_result", "errors"})


def _provider_adapter_failure(status: str, code: str) -> dict[str, Any]:
    return {"status": status, "errors": [code]}


def build_provider_recommendation_payload(*, prepared_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Build a serialized provider-neutral payload from a ready prepared cycle."""
    if not isinstance(prepared_cycle, Mapping) or prepared_cycle.get("status") != "ready":
        return _provider_adapter_failure("prepared_cycle_not_ready", "prepared_cycle_not_ready")
    if not set(prepared_cycle) <= _PREPARED_CYCLE_KEYS:
        return _provider_adapter_failure("provider_payload_validation_failed", "provider_payload_validation_failed")
    request = prepared_cycle.get("recommendation_request")
    if not isinstance(request, Mapping):
        return _provider_adapter_failure("provider_payload_validation_failed", "provider_payload_validation_failed")
    try:
        if not set(_PROVIDER_OUTBOUND_KEYS) <= set(request):
            raise ValueError("missing approved request field")
        serialize_recommendation_request(deepcopy(dict(request)))
        payload = {key: deepcopy(request[key]) for key in _PROVIDER_OUTBOUND_KEYS}
        if _RUNTIME_PROVIDER_KEY in request:
            runtime = request[_RUNTIME_PROVIDER_KEY]
            if not isinstance(runtime, Mapping):
                raise ValueError("invalid runtime projection")
            payload[_RUNTIME_PROVIDER_KEY] = deepcopy(dict(runtime))
        return serialize_recommendation_request(payload)
    except (TypeError, ValueError):
        return _provider_adapter_failure("provider_payload_validation_failed", "provider_payload_validation_failed")


def adapt_provider_recommendation_response(*, provider_response: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a provider-independent structured response without semantic evaluation."""
    if type(provider_response) is not dict:
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")
    if set(provider_response) not in (set(_PROVIDER_RESPONSE_KEYS), set(_GROUNDED_PROVIDER_RESPONSE_KEYS)):
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")
    if provider_response.get("recommendation_status") not in _PROVIDER_RESPONSE_STATUSES:
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")
    try:
        if "grounding" in provider_response:
            grounding = provider_response["grounding"]
            required = {"schema_version", "confirmed_facts", "unknown_facts", "evidence_only", "conflicts", "conditional_dependencies"}
            if not isinstance(grounding, Mapping) or set(grounding) != required or grounding.get("schema_version") != "grounding-v1" or not all(isinstance(grounding[key], list) for key in required - {"schema_version"}):
                raise ValueError("invalid grounding")
        return serialize_recommendation_request(deepcopy(provider_response))
    except (TypeError, ValueError):
        return _provider_adapter_failure("provider_response_validation_failed", "provider_response_validation_failed")


_GROUNDING_V1_ENTRY_KEYS = ("confirmed_facts", "unknown_facts", "evidence_only", "conflicts", "conditional_dependencies")


def grounding_structure_diagnostic(grounding: Any) -> str | None:
    """Return one bounded structural code without exposing response values."""
    if grounding is None:
        return "grounding_missing"
    if not isinstance(grounding, Mapping):
        return "grounding_not_mapping"
    allowed = {"schema_version", *_GROUNDING_V1_ENTRY_KEYS}
    if any(key not in allowed for key in grounding):
        return "grounding_unknown_field"
    if "schema_version" not in grounding:
        return "grounding_version_missing"
    if grounding.get("schema_version") != "grounding-v1":
        return "grounding_version_invalid"
    for key in _GROUNDING_V1_ENTRY_KEYS:
        if key not in grounding:
            return "grounding_entries_missing"
        if not isinstance(grounding[key], list):
            return "grounding_entries_not_list"
        for entry in grounding[key]:
            if not isinstance(entry, Mapping):
                return "grounding_entry_not_mapping"
            if "path" not in entry:
                return "grounding_entry_field_missing"
            if not isinstance(entry["path"], str) or not entry["path"]:
                return "grounding_entry_field_invalid"
    return None


def validate_runtime_grounding(*, runtime_advice_state: Mapping[str, Any], grounding: Mapping[str, Any], legacy_compatible: bool = False, user_answer: str = "") -> list[str]:
    """Return deterministic grounding errors without reading raw runtime state."""
    if not isinstance(runtime_advice_state, Mapping):
        return ["missing_runtime_projection"]
    diagnostic = grounding_structure_diagnostic(grounding)
    if diagnostic:
        return [] if legacy_compatible and diagnostic == "grounding_missing" else [diagnostic]
    facts: dict[str, Mapping[str, Any]] = {}
    def collect(value: Any, prefix: str = "") -> None:
        if isinstance(value, Mapping) and value.get("status") in {"known", "known_absent", "unknown"}:
            facts[prefix] = value; return
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key not in {"schema_version", "session_id"}:
                    collect(item, f"{prefix}.{key}" if prefix else str(key))
    collect(runtime_advice_state)
    seen: set[str] = set(); errors: list[str] = []
    categories = set(_GROUNDING_V1_ENTRY_KEYS)
    for category in categories:
        for entry in grounding[category]:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str) or not entry["path"]:
                errors.append("grounding_entry_field_invalid"); continue
            path = entry["path"]
            if any(token in path.lower() for token in ("fingerprint", "cas", "ledger", "token", "thread", "reducer", "persistence")):
                errors.append("internal_metadata_grounding"); continue
            if category in {"confirmed_facts", "unknown_facts"}:
                if path not in facts or path in seen:
                    errors.append("grounding_fact_missing_or_duplicate"); continue
                seen.add(path)
                status = facts[path].get("status")
                if category == "unknown_facts" and status != "unknown": errors.append("unknown_misclassification")
                if category == "confirmed_facts" and status == "unknown": errors.append("unknown_promoted")
                if category == "confirmed_facts" and entry.get("status") != status: errors.append("runtime_fact_contradiction")
                if status == "known" and entry.get("value") != facts[path].get("value"): errors.append("runtime_fact_contradiction")
    forbidden = ("fingerprint", "cas", "reducer", "ledger", "request token", "thread identity", "runtime_advice_state")
    if any(term in user_answer.lower() for term in forbidden): errors.append("internal_metadata_in_answer")
    return sorted(set(errors))


def run_offline_recommendation_provider_adapter(*, prepared_cycle: Mapping[str, Any], fake_provider: Any) -> dict[str, Any]:
    """Exercise a supplied in-memory provider boundary without network or retry behavior."""
    payload = build_provider_recommendation_payload(prepared_cycle=prepared_cycle)
    if "status" in payload and "errors" in payload:
        return {"status": payload["status"], "prepared_cycle": deepcopy(dict(prepared_cycle)) if isinstance(prepared_cycle, Mapping) else {}, "response_payload": None, "errors": list(payload["errors"])}
    if not callable(fake_provider):
        return {"status": "provider_unavailable", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_unavailable"]}
    try:
        raw_response = fake_provider(deepcopy(payload))
    except Exception:
        return {"status": "provider_unavailable", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_unavailable"]}
    if type(raw_response) is not dict:
        return {"status": "provider_response_malformed", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_response_malformed"]}
    adapted = adapt_provider_recommendation_response(provider_response=raw_response)
    if "status" in adapted and "errors" in adapted:
        return {"status": "provider_response_validation_failed", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": None, "errors": ["provider_response_validation_failed"]}
    return {"status": "provider_response_ready", "prepared_cycle": deepcopy(dict(prepared_cycle)), "response_payload": deepcopy(adapted), "errors": []}


def run_offline_recommendation_cycle(*, selected_moves: Sequence[Any], battle_input: Mapping[str, Any], move_repository: Any, fake_provider: Any) -> dict[str, Any]:
    """Compose the existing pure UI, fake-provider, and response boundaries."""
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=selected_moves,
        battle_input=battle_input,
        move_repository=move_repository,
    )
    if prepared.get("status") != "ready":
        return {
            "status": "preparation_not_ready",
            "prepared_cycle": deepcopy(prepared),
            "provider_stage": None,
            "completed_cycle": None,
            "errors": ["preparation_not_ready"],
        }
    provider_stage = run_offline_recommendation_provider_adapter(
        prepared_cycle=prepared,
        fake_provider=fake_provider,
    )
    if provider_stage.get("status") != "provider_response_ready":
        return {
            "status": provider_stage.get("status", "provider_response_validation_failed"),
            "prepared_cycle": deepcopy(prepared),
            "provider_stage": deepcopy(provider_stage),
            "completed_cycle": None,
            "errors": list(provider_stage.get("errors", ["provider_response_validation_failed"])),
        }
    completed = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload=provider_stage["response_payload"],
    )
    return {
        "status": completed["status"],
        "prepared_cycle": deepcopy(prepared),
        "provider_stage": deepcopy(provider_stage),
        "completed_cycle": deepcopy(completed),
        "errors": list(completed.get("errors", ())),
    }


def build_recommendation_presentation_model(*, completed_cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Build a copied UI-neutral model from a validated completion only."""
    empty = {
        "status": "validation_failed",
        "recommended_move": None,
        "recommended_slot_index": None,
        "primary_reasons": [],
        "risks": [],
        "alternatives": [],
        "candidate_summaries": [],
        "errors": ["invalid_completed_cycle"],
    }
    if not isinstance(completed_cycle, Mapping):
        return empty
    try:
        candidates = serialize_recommendation_request(deepcopy(list(completed_cycle.get("candidates", ()))))
    except (TypeError, ValueError):
        return empty
    errors = completed_cycle.get("errors", ())
    sanitized_errors = [error for error in errors if isinstance(error, str)] if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)) else []
    result = completed_cycle.get("recommendation_result")
    if completed_cycle.get("status") not in {"resolved", "insufficient_context", "no_usable_candidate"} or not isinstance(result, Mapping):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": sanitized_errors or ["response_validation_failed"],
        }
    required = {"status", "recommended_move", "recommended_slot_index", "primary_reasons", "risks", "alternatives", "errors"}
    if not required <= set(result) or result.get("status") != completed_cycle.get("status"):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": sanitized_errors or ["response_validation_failed"],
        }
    try:
        approved = serialize_recommendation_request({key: deepcopy(result[key]) for key in required})
    except (TypeError, ValueError):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": ["response_validation_failed"],
        }
    if not all(isinstance(approved[key], list) for key in ("primary_reasons", "risks", "alternatives", "errors")):
        return {
            **empty,
            "candidate_summaries": deepcopy(candidates),
            "errors": ["response_validation_failed"],
        }
    return {
        "status": approved["status"],
        "recommended_move": approved["recommended_move"],
        "recommended_slot_index": approved["recommended_slot_index"],
        "primary_reasons": deepcopy(approved["primary_reasons"]),
        "risks": deepcopy(approved["risks"]),
        "alternatives": deepcopy(approved["alternatives"]),
        "candidate_summaries": deepcopy(candidates),
        "errors": deepcopy(approved["errors"]),
    }
