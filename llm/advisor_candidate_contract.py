"""Pure v14.1 design contracts; no evaluation or provider orchestration."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from copy import deepcopy

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

def evaluate_move_candidate(*, slot_index: int, move: Any, battle_snapshot: Mapping[str, Any], repositories: Any) -> dict[str, Any]:
    """Pure v14.2 slot evaluator; isolates metadata failures per candidate."""
    if not isinstance(slot_index, int) or not 0 <= slot_index < 4: raise ValueError("invalid slot index")
    if not isinstance(move, str) or not move:
        return {"slot_index":slot_index,"move":"unknown","status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["invalid_move_identity"]}
    try:
        metadata = repositories.get(move) if hasattr(repositories, "get") else repositories[move]
    except Exception:
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["move_metadata_unavailable"]}
    if not isinstance(metadata, Mapping):
        return {"slot_index":slot_index,"move":move,"status":"unavailable","availability":"unavailable","self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":["move_metadata_unavailable"]}
    if metadata.get("category") == "status":
        return {"slot_index":slot_index,"move":move,"status":"partial","availability":"partially_evaluable","damage":{"status":"not_applicable"},"self_effects":[],"dynamic_move":None,"warnings":["unsupported_non_damage_utility_ranking"],"unavailable_reasons":[]}
    return {"slot_index":slot_index,"move":move,"status":"resolved","availability":"usable","damage":{"status":"resolved","minimum":metadata.get("minimum",0),"maximum":metadata.get("maximum",0)},"self_effects":[],"dynamic_move":None,"warnings":[],"unavailable_reasons":[]}

def evaluate_move_slots(*, moves: Sequence[Any], battle_snapshot: Mapping[str, Any], repositories: Any, maximum_slots: int = 4) -> list[dict[str, Any]]:
    if isinstance(moves, (str, bytes)) or not isinstance(moves, Sequence) or len(moves) > maximum_slots: raise ValueError("invalid move slots")
    return [evaluate_move_candidate(slot_index=index, move=move, battle_snapshot=deepcopy(dict(battle_snapshot)), repositories=repositories) for index, move in enumerate(moves) if move is not None]
