"""Strict per-hit applicability for Multiscale and Shadow Shield."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.modifiers._q12 import MUL_0_5
from advisor.damage.q12 import Q12_ONE


SCHEMA_VERSION = "full-hp-defender-ability-applicability-v1"
FULL_HP_DEFENDER_ABILITIES = frozenset({"multiscale", "shadow-shield"})
_HP_SOURCES = frozenset({
    "runtime_strategy_d0_v1",
    "detached_switch_first_defender_hp_v1",
    "detached_path_local_defender_hp_v1",
})
_BYPASS_POLICIES = {"multiscale": "mold_breaker_breakable", "shadow-shield": "mold_breaker_immune"}


def resolve_full_hp_defender_ability_applicability(
    *, ability: Any, current_hp: Any, max_hp: Any, hp_source: Any,
    suppression_status: Any, bypass_result: Any,
    source_hit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one exact pre-hit full-HP damage-modifier opportunity."""
    if ability is None or ability == "unknown":
        return _result("incomplete", "full_hp_defender_ability_unknown")
    if ability not in FULL_HP_DEFENDER_ABILITIES:
        return _result("not_applicable", "not_full_hp_defender_ability")
    if hp_source not in _HP_SOURCES:
        return _result("rejected", "full_hp_defender_hp_source_invalid")
    if not _hp_values(current_hp, max_hp):
        return _result("rejected", "full_hp_defender_hp_authority_invalid")
    if suppression_status not in {"active", "suppressed"}:
        return _result("incomplete", "full_hp_defender_suppression_unknown")
    if bypass_result not in {"not_bypassed", "bypassed"}:
        return _result("incomplete", "full_hp_defender_bypass_unknown")
    if source_hit is not None and not _valid_source_hit(source_hit):
        return _result("rejected", "full_hp_defender_source_hit_invalid")

    full_hp = current_hp == max_hp
    applies = full_hp and suppression_status == "active" and bypass_result == "not_bypassed"
    modifier = MUL_0_5 if applies else Q12_ONE
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "ability": ability, "defender_current_hp": current_hp,
        "defender_max_hp": max_hp, "defender_hp_source": hp_source,
        "full_hp": full_hp, "suppression_status": suppression_status,
        "bypass_policy": _BYPASS_POLICIES[ability], "bypass_result": bypass_result,
        "source_hit": deepcopy(dict(source_hit)) if isinstance(source_hit, Mapping) else None,
        "outcome": "applicable" if applies else "not_applicable",
        "modifier_q12": modifier,
        "fraction": {"numerator": modifier, "denominator": Q12_ONE},
        "provenance": "canonical_full_hp_defender_ability_applicability_v1",
    }


def validate_full_hp_defender_ability_applicability(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("status") != "resolved":
        return False
    ability = value.get("ability")
    hp, maximum = value.get("defender_current_hp"), value.get("defender_max_hp")
    source_hit = value.get("source_hit")
    if ability not in FULL_HP_DEFENDER_ABILITIES or not _hp_values(hp, maximum):
        return False
    if value.get("defender_hp_source") not in _HP_SOURCES or value.get("suppression_status") not in {"active", "suppressed"} or value.get("bypass_result") not in {"not_bypassed", "bypassed"}:
        return False
    if value.get("bypass_policy") != _BYPASS_POLICIES[ability] or (source_hit is not None and not _valid_source_hit(source_hit)):
        return False
    full_hp = hp == maximum
    applies = full_hp and value["suppression_status"] == "active" and value["bypass_result"] == "not_bypassed"
    modifier = MUL_0_5 if applies else Q12_ONE
    return (
        value.get("full_hp") is full_hp
        and value.get("outcome") == ("applicable" if applies else "not_applicable")
        and value.get("modifier_q12") == modifier
        and value.get("fraction") == {"numerator": modifier, "denominator": Q12_ONE}
        and value.get("provenance") == "canonical_full_hp_defender_ability_applicability_v1"
    )


def _hp_values(current_hp: Any, max_hp: Any) -> bool:
    return isinstance(current_hp, int) and not isinstance(current_hp, bool) and isinstance(max_hp, int) and not isinstance(max_hp, bool) and max_hp > 0 and 0 <= current_hp <= max_hp


def _valid_source_hit(value: Mapping[str, Any]) -> bool:
    return isinstance(value.get("hit_index"), int) and not isinstance(value.get("hit_index"), bool) and value["hit_index"] >= 1 and isinstance(value.get("path_id"), str) and bool(value["path_id"])


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
