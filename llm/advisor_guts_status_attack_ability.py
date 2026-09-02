"""Pure Guts status-attack applicability records."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.q12 import M_STAB, Q12_ONE


SCHEMA_VERSION = "guts-status-attack-ability-applicability-v1"
QUALIFYING_GUTS_CONDITIONS = frozenset({"burn", "poison", "toxic", "paralysis", "sleep", "freeze"})
_CONDITION_SOURCES = frozenset({
    "runtime_strategy_d0_v1",
    "detached_intermediate_condition_v1",
    "detached_path_local_attacker_condition_v1",
})


def resolve_guts_status_attack_ability_applicability(
    *,
    ability: Any,
    attacker_condition: Any,
    condition_source: Any,
    move_category: Any,
    suppression_status: Any,
    source_hit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one exact Guts modifier opportunity without mutating state."""
    if ability is None or ability == "unknown":
        return _result("incomplete", "guts_attacker_ability_unknown")
    if ability != "guts":
        return _result("not_applicable", "not_guts")
    if suppression_status not in {"active", "suppressed"}:
        return _result("incomplete", "guts_suppression_unknown")
    if condition_source not in _CONDITION_SOURCES:
        return _result("rejected", "guts_condition_source_invalid")
    if attacker_condition not in {*QUALIFYING_GUTS_CONDITIONS, "none"}:
        return _result("rejected", "guts_condition_invalid")
    if move_category not in {"physical", "special"}:
        return _result("incomplete", "guts_move_category_unknown")
    if source_hit is not None and not _valid_source_hit(source_hit):
        return _result("rejected", "guts_source_hit_invalid")

    condition_matches = attacker_condition in QUALIFYING_GUTS_CONDITIONS
    physical = move_category == "physical"
    suppressed = suppression_status == "suppressed"
    applies = condition_matches and physical and not suppressed
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "ability": "guts",
        "attacker_condition": attacker_condition,
        "condition_source": condition_source,
        "condition_matches": condition_matches,
        "move_category": move_category,
        "physical_attack": physical,
        "suppression_status": suppression_status,
        "source_hit": deepcopy(dict(source_hit)) if isinstance(source_hit, Mapping) else None,
        "outcome": "applicable" if applies else "not_applicable",
        "modifier_q12": M_STAB if applies else Q12_ONE,
        "fraction": {"numerator": M_STAB if applies else Q12_ONE, "denominator": Q12_ONE},
        "burn_penalty_bypassed": applies and attacker_condition == "burn",
        "provenance": "canonical_guts_status_attack_ability_applicability_v1",
    }


def validate_guts_status_attack_ability_applicability(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("status") != "resolved":
        return False
    condition = value.get("attacker_condition")
    if value.get("ability") != "guts" or condition not in {*QUALIFYING_GUTS_CONDITIONS, "none"}:
        return False
    if value.get("condition_source") not in _CONDITION_SOURCES:
        return False
    if value.get("move_category") not in {"physical", "special"}:
        return False
    if value.get("suppression_status") not in {"active", "suppressed"}:
        return False
    source_hit = value.get("source_hit")
    if source_hit is not None and not _valid_source_hit(source_hit):
        return False
    condition_matches = condition in QUALIFYING_GUTS_CONDITIONS
    physical = value.get("move_category") == "physical"
    applies = condition_matches and physical and value.get("suppression_status") != "suppressed"
    expected_modifier = M_STAB if applies else Q12_ONE
    return (
        value.get("condition_matches") is condition_matches
        and value.get("physical_attack") is physical
        and value.get("outcome") == ("applicable" if applies else "not_applicable")
        and value.get("modifier_q12") == expected_modifier
        and value.get("fraction") == {"numerator": expected_modifier, "denominator": Q12_ONE}
        and value.get("burn_penalty_bypassed") is (applies and condition == "burn")
        and value.get("provenance") == "canonical_guts_status_attack_ability_applicability_v1"
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
