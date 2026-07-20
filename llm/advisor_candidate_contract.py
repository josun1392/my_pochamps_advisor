"""Pure v14.1 design contracts; no evaluation or provider orchestration."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from copy import deepcopy
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
