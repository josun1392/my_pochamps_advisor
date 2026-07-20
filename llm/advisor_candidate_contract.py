"""Pure v14.1 design contracts; no evaluation or provider orchestration."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from copy import deepcopy
import math

from llm.advisor_battle_state_context import build_deterministic_calculation_context

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
    return build_deterministic_calculation_context(
        snapshot.get("final_stat_context"), snapshot.get("stat_stage_context"), selected_move,
        snapshot.get("current_hp_context"), snapshot.get("pokemon"), snapshot.get("condition_context"),
        snapshot.get("field_state_context"), snapshot.get("battle_format_context"), snapshot.get("opponent_selected_move"),
        snapshot.get("attacker_level_context"), snapshot.get("observed_previous_damage_context"),
        snapshot.get("battle_counter_context"), snapshot.get("consecutive_use_context"),
        snapshot.get("weight_context"), snapshot.get("turn_event_context"),
    )


def evaluate_move_candidate(*, slot_index: int, move: Any, battle_snapshot: Mapping[str, Any], repositories: Any) -> dict[str, Any]:
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
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":{"status":"not_applicable"},"self_effects":[],"dynamic_move":None,"warnings":["unsupported_non_damage_utility_ranking"],"unavailable_reasons":[]}
    snapshot = battle_snapshot if isinstance(battle_snapshot, Mapping) else {}
    context = _production_context(snapshot, _selected_move_from_metadata(move, metadata))
    dynamic_move = _dynamic_summary(context)
    damage = _damage_summary(context)
    optional_outputs, self_effects, optional_reasons = _optional_outputs(context)
    if dynamic_move is not None and dynamic_move["status"] != "resolved":
        reasons = ["required_dynamic_context_unavailable"]
        assessment = context.get(dynamic_move["assessment_key"]) if isinstance(context, Mapping) else None
        if isinstance(assessment, Mapping) and isinstance(assessment.get("reason"), str): reasons.append(assessment["reason"])
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","damage":damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":reasons,**optional_outputs}
    if damage["status"] != "resolved":
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":[damage["reason"], *optional_reasons],**optional_outputs}
    if optional_reasons:
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":optional_reasons,**optional_outputs}
    return {"slot_index":slot_index,"move":move,"status":"resolved","availability":"usable","damage":damage,"self_effects":self_effects,"dynamic_move":dynamic_move,"warnings":[],"unavailable_reasons":[],**optional_outputs}

def evaluate_move_slots(*, moves: Sequence[Any], battle_snapshot: Mapping[str, Any], repositories: Any, maximum_slots: int = 4) -> list[dict[str, Any]]:
    if isinstance(moves, (str, bytes)) or not isinstance(moves, Sequence) or len(moves) > maximum_slots: raise ValueError("invalid move slots")
    return [evaluate_move_candidate(slot_index=index, move=move, battle_snapshot=deepcopy(dict(battle_snapshot)), repositories=repositories) for index, move in enumerate(moves) if move is not None]

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
    return {
        "request_version": "v14.3",
        "readiness": {"status": "invalid_evidence_bundle", "selectable_candidate_count": 0},
        "battle_snapshot_summary": {}, "candidate_exact_set": [],
        "selectable_candidate_exact_set": [], "candidate_comparisons": [],
        "known_limitations": [], "guardrails": deepcopy(_RECOMMENDATION_GUARDRAILS),
    }


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
            comparisons.append({**deepcopy(normalized), "eligibility": eligibility})
            pairs.append(pair)
        if not all(isinstance(item, str) for item in limitations):
            raise ValueError("invalid known limitations")
    except (TypeError, ValueError):
        return _invalid_request()
    selectable = [deepcopy(pair) for pair, row in zip(pairs, comparisons, strict=True) if row["eligibility"] != "not_selectable"]
    readiness = "no_candidates" if not pairs else "ready" if selectable else "no_selectable_candidates"
    return {
        "request_version": "v14.3",
        "readiness": {"status": readiness, "selectable_candidate_count": len(selectable)},
        "battle_snapshot_summary": deepcopy(dict(snapshot)),
        "candidate_exact_set": deepcopy(pairs),
        "selectable_candidate_exact_set": selectable,
        "candidate_comparisons": comparisons,
        "known_limitations": deepcopy(limitations),
        "guardrails": deepcopy(_RECOMMENDATION_GUARDRAILS),
    }


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
