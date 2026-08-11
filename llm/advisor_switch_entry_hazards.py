"""Frozen candidate-local Stealth Rock and Spikes entry evaluation."""
from __future__ import annotations

from typing import Any, Mapping

from advisor.damage.types import TYPES, type_effectiveness


_SPIKES_DIVISORS = {1: 8, 2: 6, 3: 4}


def evaluate_entry_hazards(*, hazards: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate only supported entry damage from frozen, candidate-B authority.

    A known Heavy-Duty Boots or Magic Guard record proves that both supported
    hazards deal zero damage.  Otherwise every relevant authority must be
    exact; unknown facts deliberately leave this result incomplete.
    """
    hp = target.get("hp_authority") if isinstance(target, Mapping) else None
    item = target.get("item_authority") if isinstance(target, Mapping) else None
    ability = target.get("ability_authority") if isinstance(target, Mapping) else None
    if _known_value(item) == "heavy-duty-boots" or _known_value(ability) == "magic-guard":
        return _complete(damage=0, hp=hp, reason="entry_damage_exception")
    if not _known_authority(item) or not _known_authority(ability):
        return _incomplete("entry_modifier_unknown")
    if not _valid_hp(hp):
        return _incomplete("hp_unknown")

    rock, spikes = _hazard_values(hazards)
    if rock is None or spikes is None:
        return _incomplete("hazard_unknown")

    damage = 0
    if rock == "present":
        types = target.get("current_type_authority")
        if not _valid_current_types(types):
            return _incomplete("current_type_unknown")
        # The repository's canonical effectiveness helper returns the Q12
        # multiplier used by deterministic damage mechanics.
        damage += _fractional_max_hp_damage(hp["maximum_hp"], numerator=type_effectiveness("rock", tuple(types["value"])), denominator=8 * 4096)
    if spikes:
        grounded = target.get("prospective_groundedness_authority")
        if not isinstance(grounded, Mapping) or grounded.get("status") not in {"grounded", "ungrounded"} or set(grounded) != {"status"}:
            return _incomplete("prospective_groundedness_unknown")
        if grounded["status"] == "grounded":
            damage += _fractional_max_hp_damage(hp["maximum_hp"], numerator=1, denominator=_SPIKES_DIVISORS[spikes])
    return _complete(damage=damage, hp=hp, reason=None)


def _hazard_values(hazards: Mapping[str, Any]) -> tuple[str | None, int | None]:
    required = {"schema_version", "session_id", "affected_side", "stealth_rock", "spikes_layers"}
    if not isinstance(hazards, Mapping) or not required.issubset(hazards) or hazards.get("schema_version") not in {"switch-hazard-context-v1", "switch-hazard-context-v2"} or hazards.get("affected_side") != "self":
        return None, None
    rock, spikes = hazards.get("stealth_rock"), hazards.get("spikes_layers")
    if rock not in {"present", "absent"} or spikes not in {*_SPIKES_DIVISORS, 0}:
        return None, None
    return rock, spikes


def _valid_hp(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("status") == "known"
        and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool)
        and isinstance(value.get("maximum_hp"), int) and not isinstance(value.get("maximum_hp"), bool)
        and 0 <= value["current_hp"] <= value["maximum_hp"]
        and value["maximum_hp"] > 0
    )


def _valid_current_types(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("value"), list) and 1 <= len(value["value"]) <= 2 and all(type_ in TYPES for type_ in value["value"])


def _known_authority(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "known" and set(value) == {"status", "value"}


def _known_value(value: Any) -> Any:
    return value.get("value") if _known_authority(value) else None


def _fractional_max_hp_damage(maximum_hp: int, *, numerator: int, denominator: int) -> int:
    return max(1, maximum_hp * numerator // denominator)


def _incomplete(reason: str) -> dict[str, Any]:
    return {"status": "insufficient_context", "damage": None, "reason": reason, "post_hazard_hp": None, "hazard_ko": None}


def _complete(*, damage: int, hp: Any, reason: str | None) -> dict[str, Any]:
    current = hp.get("current_hp") if isinstance(hp, Mapping) else None
    has_current_hp = isinstance(current, int) and not isinstance(current, bool) and current >= 0
    return {
        "status": "complete",
        "damage": damage,
        "reason": reason,
        "post_hazard_hp": max(0, current - damage) if has_current_hp else None,
        "hazard_ko": current <= damage if has_current_hp else False if damage == 0 else None,
    }
