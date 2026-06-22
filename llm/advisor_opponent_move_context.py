"""Source-bound opponent move context helper.

This helper normalizes caller-provided opponent move facts and candidates. It
does not infer hidden movesets, selected moves, items, spreads, or turn results.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES = frozenset(
    {
        "user_confirmed",
        "visible_ui",
        "explicit_input",
    }
)
OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES = frozenset(
    {
        "visible_or_cache_candidate",
        "champions_movepool",
        "visible_ui",
    }
)
OPPONENT_MOVE_CONTEXT_ALLOWED_MOVE_FIELDS = frozenset(
    {
        "move_id",
        "name",
        "type",
        "category",
        "power",
        "accuracy",
        "priority",
        "target",
        "effect_flags",
        "source",
        "confirmed",
        "selected",
    }
)
OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS = frozenset(
    {
        "inferred_moveset",
        "predicted_move",
        "likely_move",
        "will_use",
        "usage_rate_guess",
        "meta_set",
        "EVs",
        "IVs",
        "nature",
        "hidden_item",
        "post_turn_hp",
        "item_consumed",
        "rng_resolved",
        "speed_tie_resolved",
    }
)
OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES = (
    "hidden moveset inference",
    "opponent set inference",
    "selected opponent move inference",
    "EV/IV/nature inference",
    "hidden item inference",
    "weather/terrain/boost inference",
    "RNG resolution",
    "full turn resolution",
)
OPPONENT_MOVE_CONTEXT_SAFETY_NOTES = (
    "Candidate moves are not confirmed selected moves.",
    "Only explicitly known or visible move data should be treated as known.",
)


def build_opponent_move_context(
    *,
    known_moves: Sequence[Mapping[str, Any]] | None = None,
    candidate_moves: Sequence[Mapping[str, Any]] | None = None,
    selected_opponent_move: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build limited opponent move context from explicit caller-provided data."""
    known = _known_moves(known_moves)
    candidates = _candidate_moves(candidate_moves)
    selected = _selected_opponent_move(selected_opponent_move)

    return {
        "kind": "opponent_move_context",
        "confidence": _confidence(known_moves=known, candidate_moves=candidates, selected_opponent_move=selected),
        "selected_opponent_move": selected,
        "known_opponent_moves": known,
        "candidate_moves": candidates,
        "priority_move_candidates": _priority_move_candidates(candidates),
        "unsupported": list(OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES),
        "safety_notes": list(OPPONENT_MOVE_CONTEXT_SAFETY_NOTES),
    }


def _confidence(
    *,
    known_moves: Sequence[Mapping[str, Any]],
    candidate_moves: Sequence[Mapping[str, Any]],
    selected_opponent_move: Mapping[str, Any],
) -> str:
    if known_moves or candidate_moves or selected_opponent_move.get("status") == "explicit":
        return "limited"
    return "unknown"


def _known_moves(moves: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if moves is None:
        return []
    normalized: list[dict[str, Any]] = []
    for move in moves:
        source = move.get("source")
        if source not in OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES:
            continue
        normalized_move = _normalized_move(move, source=str(source))
        normalized_move["confirmed"] = True
        normalized.append(normalized_move)
    return normalized


def _candidate_moves(moves: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if moves is None:
        return []
    normalized: list[dict[str, Any]] = []
    for move in moves:
        source = move.get("source")
        if source not in OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES:
            continue
        if _has_selected_or_confirmed_semantics(move):
            continue
        normalized_move = _normalized_move(move, source=str(source))
        normalized_move["confirmed"] = False
        normalized_move["selected"] = False
        normalized.append(normalized_move)
    return normalized


def _selected_opponent_move(move: Mapping[str, Any] | None) -> dict[str, Any]:
    if move is None:
        return {"status": "unknown"}

    status = move.get("status", "explicit")
    if status == "unknown":
        return {"status": "unknown"}
    if status != "explicit":
        raise ValueError("selected_opponent_move must be unknown or explicit")

    source = move.get("source")
    if source not in OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES:
        raise ValueError("explicit selected_opponent_move requires a trusted source")
    selected = {"status": "explicit"}
    for key in ("source", "move_id", "name"):
        if move.get(key) is not None:
            selected[key] = move[key]
    if not selected.get("move_id") or not selected.get("name"):
        raise ValueError("explicit selected_opponent_move requires move_id and name")
    return selected


def _priority_move_candidates(candidate_moves: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    priority_candidates: list[dict[str, Any]] = []
    for move in candidate_moves:
        priority = move.get("priority")
        if not isinstance(priority, int) or priority <= 0:
            continue
        priority_candidates.append(
            {
                "source": move["source"],
                "move_id": move.get("move_id"),
                "name": move.get("name"),
                "priority": priority,
                "confirmed": False,
                "selected": False,
            }
        )
    return priority_candidates


def _normalized_move(move: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    normalized = {
        key: value
        for key, value in move.items()
        if key in OPPONENT_MOVE_CONTEXT_ALLOWED_MOVE_FIELDS
        and key not in OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS
        and value is not None
    }
    normalized["source"] = source
    return normalized


def _has_selected_or_confirmed_semantics(move: Mapping[str, Any]) -> bool:
    return any(
        move.get(key) is True
        for key in (
            "confirmed",
            "selected",
            "will_use",
            "likely_selected",
        )
    )
