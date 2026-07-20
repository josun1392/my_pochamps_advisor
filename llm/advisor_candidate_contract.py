"""Pure v14.1 design contracts; no evaluation or provider orchestration."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any

CANDIDATE_STATUSES = frozenset({"resolved", "partial", "unavailable"})
RECOMMENDATION_STATUSES = frozenset({"resolved", "insufficient_context", "no_usable_candidate", "validation_failed"})

def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    required = {"move", "status", "availability", "self_effects", "dynamic_move", "warnings", "unavailable_reasons"}
    if not required <= set(candidate) or not isinstance(candidate.get("move"), str) or candidate.get("status") not in CANDIDATE_STATUSES:
        raise ValueError("invalid candidate schema")
    if not all(isinstance(candidate[key], list) for key in ("self_effects", "warnings", "unavailable_reasons")):
        raise ValueError("invalid candidate collections")
    return dict(candidate)

def build_evidence_bundle(snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], limitations: Sequence[str]) -> dict[str, Any]:
    normalized = [validate_candidate(candidate) for candidate in candidates]
    return {"battle_snapshot_summary": dict(snapshot), "candidates": normalized, "comparison_policy": {"allow_partial_candidates": True, "no_untrusted_inference": True}, "known_limitations": list(limitations)}

def validate_recommendation(response: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status = response.get("recommendation_status")
    if status not in RECOMMENDATION_STATUSES: raise ValueError("invalid recommendation status")
    moves = {candidate["move"] for candidate in candidates}
    move = response.get("recommended_move")
    if status == "resolved" and (not isinstance(move, str) or move not in moves): raise ValueError("recommendation outside candidate exact-set")
    if any(key not in response or not isinstance(response[key], list) for key in ("primary_reasons", "risks", "alternatives")): raise ValueError("invalid recommendation evidence")
    return dict(response)
