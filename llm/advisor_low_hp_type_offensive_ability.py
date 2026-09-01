"""Pure low-HP type offensive ability applicability records."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.q12 import M_STAB, Q12_ONE


SCHEMA_VERSION = "low-hp-type-offensive-ability-applicability-v1"
LOW_HP_TYPE_OFFENSIVE_ABILITIES = {
    "blaze": "fire",
    "torrent": "water",
    "overgrow": "grass",
    "swarm": "bug",
}
_HP_SOURCES = {"runtime_strategy_d0_v1", "detached_path_local_attacker_hp_v1"}


def resolve_low_hp_type_offensive_ability_applicability(
    *,
    ability: Any,
    effective_move_type: Any,
    current_hp: Any,
    max_hp: Any,
    hp_source: Any,
    source_hit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one exact damage event without mutating D0 or path state."""
    if ability is None or ability == "unknown":
        return _result("incomplete", "low_hp_type_attacker_ability_unknown")
    if ability not in LOW_HP_TYPE_OFFENSIVE_ABILITIES:
        return _result("not_applicable", "not_low_hp_type_offensive_ability")
    if not isinstance(effective_move_type, str) or not effective_move_type or effective_move_type == "unknown":
        return _result("incomplete", "low_hp_type_effective_move_type_unknown")
    if hp_source not in _HP_SOURCES:
        return _result("rejected", "low_hp_type_hp_source_invalid")
    if not _hp_values(current_hp, max_hp):
        return _result("rejected", "low_hp_type_hp_authority_invalid")
    if source_hit is not None and not _valid_source_hit(source_hit):
        return _result("rejected", "low_hp_type_source_hit_invalid")

    required_type = LOW_HP_TYPE_OFFENSIVE_ABILITIES[ability]
    threshold_active = current_hp * 3 <= max_hp
    type_matches = effective_move_type == required_type
    applies = threshold_active and type_matches
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "ability": ability,
        "required_move_type": required_type,
        "effective_move_type": effective_move_type,
        "type_matches": type_matches,
        "threshold": {
            "expression": "current_hp * 3 <= max_hp",
            "current_hp": current_hp,
            "max_hp": max_hp,
            "active": threshold_active,
        },
        "hp_source": hp_source,
        "source_hit": deepcopy(dict(source_hit)) if isinstance(source_hit, Mapping) else None,
        "outcome": "applicable" if applies else "not_applicable",
        "modifier_q12": M_STAB if applies else Q12_ONE,
        "fraction": {"numerator": M_STAB if applies else Q12_ONE, "denominator": Q12_ONE},
        "provenance": "canonical_low_hp_type_offensive_ability_applicability_v1",
    }


def validate_low_hp_type_offensive_ability_applicability(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("status") != "resolved":
        return False
    ability = value.get("ability")
    required = LOW_HP_TYPE_OFFENSIVE_ABILITIES.get(ability)
    threshold = value.get("threshold")
    source_hit = value.get("source_hit")
    if required is None or not isinstance(threshold, Mapping):
        return False
    current_hp, max_hp = threshold.get("current_hp"), threshold.get("max_hp")
    if not _hp_values(current_hp, max_hp):
        return False
    if value.get("required_move_type") != required:
        return False
    move_type = value.get("effective_move_type")
    if not isinstance(move_type, str) or not move_type:
        return False
    if value.get("hp_source") not in _HP_SOURCES:
        return False
    if source_hit is not None and not _valid_source_hit(source_hit):
        return False
    threshold_active = current_hp * 3 <= max_hp
    type_matches = move_type == required
    applies = threshold_active and type_matches
    expected_modifier = M_STAB if applies else Q12_ONE
    return (
        threshold.get("expression") == "current_hp * 3 <= max_hp"
        and threshold.get("active") is threshold_active
        and value.get("type_matches") is type_matches
        and value.get("outcome") == ("applicable" if applies else "not_applicable")
        and value.get("modifier_q12") == expected_modifier
        and value.get("fraction") == {"numerator": expected_modifier, "denominator": Q12_ONE}
        and value.get("provenance") == "canonical_low_hp_type_offensive_ability_applicability_v1"
    )


def _hp_values(current_hp: Any, max_hp: Any) -> bool:
    return (
        isinstance(current_hp, int) and not isinstance(current_hp, bool)
        and isinstance(max_hp, int) and not isinstance(max_hp, bool)
        and 0 <= current_hp <= max_hp and max_hp > 0
    )


def _valid_source_hit(value: Mapping[str, Any]) -> bool:
    hit_index = value.get("hit_index")
    path_id = value.get("path_id")
    return (
        isinstance(hit_index, int) and not isinstance(hit_index, bool) and hit_index >= 1
        and isinstance(path_id, str) and bool(path_id)
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
