"""Canonical move-use consequence labels; intentionally no outcome calculation."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from advisor.damage.move_categories import get_move_flags
from core.charge_move_repository import ChargeMoveRepository

_SELF_FAINT_MOVES = frozenset({"explosion", "self-destruct", "misty-explosion", "memento", "healing-wish", "lunar-dance"})
_FORCED_SWITCH_MOVES = frozenset({"roar", "whirlwind", "dragon-tail", "circle-throw"})
_RECHARGE_MOVES = frozenset({"hyper-beam", "giga-impact", "blast-burn", "frenzy-plant", "hydro-cannon", "rock-wrecker", "roar-of-time", "prismatic-laser", "meteor-assault", "eternabeam"})
_LOCKED_REPEAT_MOVES = frozenset({"outrage", "petal-dance", "thrash", "rollout", "ice-ball"})


def evaluate_move_consequence_evidence(*, move_id: str, metadata: Any, charge_repository: ChargeMoveRepository | None = None) -> dict[str, Any]:
    """Return only canonical labels and ratios, never HP, turns, or utility."""
    if not isinstance(move_id, str) or not move_id:
        return {"status": "insufficient_context", "consequence_tags": [], "canonical_ratio": None, "uncertainty": ["move_identity_missing"]}
    if not isinstance(metadata, Mapping) and not hasattr(metadata, "category"):
        return {"status": "insufficient_context", "consequence_tags": [], "canonical_ratio": None, "uncertainty": ["canonical_move_metadata_missing"]}
    value = metadata.get if isinstance(metadata, Mapping) else lambda key, default=None: getattr(metadata, key, default)
    if value("dynamic_consequence") is True:
        return {"status": "unsupported_mechanic", "consequence_tags": [], "canonical_ratio": None, "unsupported_reason": "dynamic_consequence_mechanic"}
    tags: list[str] = []
    ratio: int | None = None
    drain = value("drain")
    if drain is not None:
        if isinstance(drain, bool) or not isinstance(drain, int) or not -100 <= drain <= 100:
            return {"status": "unsupported_mechanic", "consequence_tags": [], "canonical_ratio": None, "unsupported_reason": "invalid_canonical_drain"}
        if drain < 0:
            tags.append("recoil")
            ratio = abs(drain)
        elif drain > 0:
            tags.append("drain_or_healing_from_damage")
            ratio = drain
    if "recoil" in get_move_flags(move_id) and "recoil" not in tags:
        tags.append("recoil")
    charge = (charge_repository or ChargeMoveRepository()).get_charge_move_metadata(move_id)
    if isinstance(charge, Mapping) and charge.get("is_charge_move") is True:
        tags.append("charge_turn")
    if move_id in _RECHARGE_MOVES:
        tags.append("recharge_turn")
    if move_id in _SELF_FAINT_MOVES:
        tags.append("self_faint")
    if move_id in _FORCED_SWITCH_MOVES:
        tags.append("forced_switch")
    if move_id in _LOCKED_REPEAT_MOVES:
        tags.append("locked_or_repeated_use")
    if not tags:
        return {"status": "no_known_consequence", "consequence_tags": [], "canonical_ratio": None, "uncertainty": []}
    return {"status": "known", "consequence_tags": tags, "canonical_ratio": ratio, "uncertainty": []}
