"""Application-owned move/switch selection over frozen danger evidence.

This module deliberately does not calculate mechanics or serialize a provider
payload.  It consumes finalized move-native ordering supplied by the existing
move path and cross-action danger projections supplied by
``advisor_cross_action_danger``.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping, Sequence
from typing import Any


_DANGER_ORDINAL = {
    "executed_guaranteed_self_ko": 0,
    "unresolved_guaranteed_self_ko_exposure": 1,
    "possible_self_ko_exposure": 2,
    "neutral_no_positive_danger": 3,
}


def select_combined_self_action(
    *,
    move_actions: Sequence[Mapping[str, Any]] | None,
    switch_actions: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Select only when application-owned eligibility and danger permit it.

    Move records may carry a precomputed ``native_move_rank`` (lower is better).
    The value is used exclusively between moves; this function never reads move
    probability, damage, effectiveness, or switch slot order as cross-kind rank.
    """
    actions, malformed_ids = _normalize_actions(move_actions, "move")
    switches, bad_switches = _normalize_actions(switch_actions, "switch")
    actions.extend(switches)
    malformed_ids.extend(bad_switches)

    selectable = [action for action in actions if action["selectable"]]
    if not selectable:
        return _result(
            selected=None,
            supportability="unsupported_mechanic" if malformed_ids else "insufficient_context",
            reason="no_selectable_action",
            compared_count=len(actions),
            malformed_ids=malformed_ids,
        )

    best_ordinal = max(action["danger_ordinal"] for action in selectable)
    best = [action for action in selectable if action["danger_ordinal"] == best_ordinal]
    moves = [action for action in best if action["action_kind"] == "move"]
    switches = [action for action in best if action["action_kind"] == "switch"]

    # This is the bounded v1 product policy: only an equal danger cross-kind
    # comparison prefers a move.  It is not a move-native mechanics comparison.
    if moves and switches:
        selected, native_reason = _best_move(moves)
        return _result(
            selected=selected,
            supportability="complete",
            reason="same_tier_move_preference" if len(moves) == 1 else native_reason,
            compared_count=len(actions),
            malformed_ids=malformed_ids,
        )
    if moves:
        selected, reason = _best_move(moves)
        return _result(selected=selected, supportability="complete", reason=reason, compared_count=len(actions), malformed_ids=malformed_ids)
    if len(switches) == 1:
        return _result(selected=switches[0], supportability="complete", reason="only_selectable_action", compared_count=len(actions), malformed_ids=malformed_ids)

    # Slot/enumeration order is retained only in the tie set; it is never a
    # strategic switch-native rank.
    return _result(
        selected=None,
        supportability="unresolved_equal_switches",
        reason="unresolved_switch_tie",
        compared_count=len(actions),
        malformed_ids=malformed_ids,
        tied_ids=[action["action_candidate_id"] for action in switches],
        selected_kind="switch",
    )


def _normalize_actions(
    records: Sequence[Mapping[str, Any]] | None,
    expected_kind: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return [], []
    normalized: list[dict[str, Any]] = []
    malformed: list[str] = []
    for raw in records:
        candidate_id = raw.get("action_candidate_id") if isinstance(raw, Mapping) else None
        if not isinstance(raw, Mapping) or not isinstance(candidate_id, str) or raw.get("action_kind") != expected_kind:
            malformed.append(candidate_id if isinstance(candidate_id, str) else "<unknown>")
            continue
        tier = raw.get("cross_action_danger_tier")
        if tier not in _DANGER_ORDINAL or not isinstance(raw.get("selectable"), bool):
            malformed.append(candidate_id)
            continue
        if expected_kind == "switch" and "native_move_rank" in raw:
            malformed.append(candidate_id)
            continue
        rank = raw.get("native_move_rank") if expected_kind == "move" else None
        if rank is not None and (not isinstance(rank, int) or isinstance(rank, bool)):
            malformed.append(candidate_id)
            continue
        normalized.append({
            "action_candidate_id": candidate_id,
            "action_kind": expected_kind,
            "selectable": raw["selectable"],
            "cross_action_danger_tier": tier,
            "danger_ordinal": _DANGER_ORDINAL[tier],
            "native_move_rank": rank,
        })
    return normalized, malformed


def _best_move(moves: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], str]:
    # A finalized native rank is optional for legacy input.  Stable incoming
    # candidate order is the compatibility fallback, never cross-kind policy.
    ranked = [(index, move) for index, move in enumerate(moves) if move.get("native_move_rank") is not None]
    if not ranked:
        return moves[0], "stable_move_inventory_order"
    _index, selected = min(ranked, key=lambda item: (item[1]["native_move_rank"], item[0]))
    return selected, "move_native_rank"


def _result(
    *,
    selected: Mapping[str, Any] | None,
    supportability: str,
    reason: str,
    compared_count: int,
    malformed_ids: Sequence[str],
    tied_ids: Sequence[str] = (),
    selected_kind: str | None = None,
) -> dict[str, Any]:
    return deepcopy({
        "selected_action_kind": selected_kind if selected is None else selected["action_kind"],
        "selected_candidate_id": None if selected is None else selected["action_candidate_id"],
        "selection_supportability": supportability,
        "selection_reason": reason,
        "compared_action_count": compared_count,
        "tied_candidate_ids": list(tied_ids),
        "malformed_candidate_ids": list(malformed_ids),
    })
