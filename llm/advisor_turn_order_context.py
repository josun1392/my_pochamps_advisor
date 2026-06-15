"""Deterministic, non-resolved turn order context helper."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


TURN_ORDER_CONTEXT_CONFIDENCE_VALUES = frozenset({"limited", "unknown"})
TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES = frozenset(
    {
        "own_higher_priority",
        "opponent_higher_priority",
        "same_priority",
        "unknown",
    }
)
TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES = frozenset(
    {
        "own_faster_by_base_speed",
        "opponent_faster_by_base_speed",
        "equal_base_speed_tie_candidate",
        "own_faster_by_confirmed_final_speed",
        "opponent_faster_by_confirmed_final_speed",
        "equal_confirmed_final_speed_tie_candidate",
        "unknown_due_to_missing_speed_data",
        "unknown_due_to_missing_priority_or_move",
    }
)
TURN_ORDER_CONTEXT_ORDER_HINT_VALUES = frozenset(
    {
        "own_likely_before_opponent_if_same_priority",
        "opponent_likely_before_own_if_same_priority",
        "priority_overrides_speed",
        "tie_or_unknown",
        "unknown",
    }
)
TURN_ORDER_CONTEXT_UNSUPPORTED_BOUNDARIES = (
    "final EV/IV/nature speed",
    "speed tie resolution",
    "RNG item activation",
    "exact final order",
    "item consumption",
    "post-turn HP update",
)
TURN_ORDER_CONTEXT_REQUIRED_UNSUPPORTED = frozenset(
    {
        "speed tie resolution",
        "RNG item activation",
        "exact final order",
        "item consumption",
        "post-turn HP update",
    }
)
TURN_ORDER_CONTEXT_FORBIDDEN_FIELDS = frozenset(
    {
        "final_order_resolved",
        "item_consumed",
        "post_turn_hp",
        "speed_tie_resolved",
        "rng_item_activated",
    }
)


def build_deterministic_turn_order_context(
    *,
    own_move_priority: int | None,
    opponent_move_priority: int | None,
    own_base_speed: int | None,
    opponent_base_speed: int | None,
    own_confirmed_final_speed: int | None = None,
    opponent_confirmed_final_speed: int | None = None,
    candidate_modifiers: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build limited turn-order context without resolving final action order."""
    priority_relation = _priority_relation(
        own_move_priority=own_move_priority,
        opponent_move_priority=opponent_move_priority,
    )
    speed = _speed_context(
        own_base_speed=own_base_speed,
        opponent_base_speed=opponent_base_speed,
        own_confirmed_final_speed=own_confirmed_final_speed,
        opponent_confirmed_final_speed=opponent_confirmed_final_speed,
    )
    order_hint = _order_hint(priority_relation=priority_relation, speed_relation=speed["speed_relation"])
    normalized_modifiers = _candidate_modifiers(candidate_modifiers)

    return {
        "kind": "deterministic_turn_order_context",
        "confidence": _confidence(priority_relation=priority_relation, speed_relation=speed["speed_relation"]),
        "priority": {
            "own_move_priority": _known_or_unknown(own_move_priority),
            "opponent_move_priority": _known_or_unknown(opponent_move_priority),
            "priority_relation": priority_relation,
        },
        "speed": speed,
        "order_hint": order_hint,
        "tie_or_unknown": _is_tie_or_unknown(priority_relation=priority_relation, speed_relation=speed["speed_relation"]),
        "candidate_modifiers": normalized_modifiers,
        "unsupported": list(TURN_ORDER_CONTEXT_UNSUPPORTED_BOUNDARIES),
    }


def _priority_relation(*, own_move_priority: int | None, opponent_move_priority: int | None) -> str:
    if own_move_priority is None or opponent_move_priority is None:
        return "unknown"
    if own_move_priority > opponent_move_priority:
        return "own_higher_priority"
    if own_move_priority < opponent_move_priority:
        return "opponent_higher_priority"
    return "same_priority"


def _speed_context(
    *,
    own_base_speed: int | None,
    opponent_base_speed: int | None,
    own_confirmed_final_speed: int | None,
    opponent_confirmed_final_speed: int | None,
) -> dict[str, Any]:
    if own_confirmed_final_speed is not None and opponent_confirmed_final_speed is not None:
        return {
            "basis": "confirmed_final_speed",
            "own_base_speed": _known_or_unknown(own_base_speed),
            "opponent_base_speed": _known_or_unknown(opponent_base_speed),
            "own_confirmed_final_speed": own_confirmed_final_speed,
            "opponent_confirmed_final_speed": opponent_confirmed_final_speed,
            "speed_relation": _speed_relation(
                own_speed=own_confirmed_final_speed,
                opponent_speed=opponent_confirmed_final_speed,
                own_value="own_faster_by_confirmed_final_speed",
                opponent_value="opponent_faster_by_confirmed_final_speed",
                equal_value="equal_confirmed_final_speed_tie_candidate",
            ),
            "final_speed_known": True,
        }
    if own_base_speed is not None and opponent_base_speed is not None:
        return {
            "basis": "base_species_stats_only",
            "own_base_speed": own_base_speed,
            "opponent_base_speed": opponent_base_speed,
            "speed_relation": _speed_relation(
                own_speed=own_base_speed,
                opponent_speed=opponent_base_speed,
                own_value="own_faster_by_base_speed",
                opponent_value="opponent_faster_by_base_speed",
                equal_value="equal_base_speed_tie_candidate",
            ),
            "final_speed_known": False,
        }
    return {
        "basis": "unknown",
        "own_base_speed": _known_or_unknown(own_base_speed),
        "opponent_base_speed": _known_or_unknown(opponent_base_speed),
        "speed_relation": "unknown_due_to_missing_speed_data",
        "final_speed_known": False,
    }


def _speed_relation(
    *,
    own_speed: int,
    opponent_speed: int,
    own_value: str,
    opponent_value: str,
    equal_value: str,
) -> str:
    if own_speed > opponent_speed:
        return own_value
    if own_speed < opponent_speed:
        return opponent_value
    return equal_value


def _order_hint(*, priority_relation: str, speed_relation: str) -> str:
    if priority_relation in {"own_higher_priority", "opponent_higher_priority"}:
        return "priority_overrides_speed"
    if priority_relation == "unknown":
        return "unknown"
    if speed_relation in {"own_faster_by_base_speed", "own_faster_by_confirmed_final_speed"}:
        return "own_likely_before_opponent_if_same_priority"
    if speed_relation in {"opponent_faster_by_base_speed", "opponent_faster_by_confirmed_final_speed"}:
        return "opponent_likely_before_own_if_same_priority"
    return "tie_or_unknown"


def _confidence(*, priority_relation: str, speed_relation: str) -> str:
    if priority_relation == "unknown" and speed_relation == "unknown_due_to_missing_speed_data":
        return "unknown"
    return "limited"


def _is_tie_or_unknown(*, priority_relation: str, speed_relation: str) -> bool:
    return (
        priority_relation == "unknown"
        or speed_relation
        in {
            "equal_base_speed_tie_candidate",
            "equal_confirmed_final_speed_tie_candidate",
            "unknown_due_to_missing_speed_data",
            "unknown_due_to_missing_priority_or_move",
        }
    )


def _candidate_modifiers(candidate_modifiers: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if candidate_modifiers is None:
        return []
    normalized: list[dict[str, Any]] = []
    for modifier in candidate_modifiers:
        normalized.append(
            {
                "source": str(modifier.get("source") or "unknown"),
                "effect": str(modifier.get("effect") or "may alter move order"),
                "resolved": False,
            }
        )
    return normalized


def _known_or_unknown(value: int | None) -> int | str:
    if value is None:
        return "unknown"
    return value
