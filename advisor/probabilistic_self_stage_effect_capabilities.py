"""Strict catalog-backed capability classification for self stage secondaries."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "probabilistic-self-stage-effect-capability-resolution-v1"
CATALOG_VERSION = "probabilistic-self-stage-effects-catalog-v1"
_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "probabilistic_self_stage_effects.json"
_ABILITY_STATUSES = frozenset({"known", "unknown"})
_APPLICABILITY = frozenset({"applicable", "not_applicable", "unknown"})
_STATS = frozenset({"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"})


def resolve_probabilistic_self_stage_effect_capability(
    *, move: Mapping[str, Any] | Any, source_authority: Mapping[str, Any] | Any,
) -> dict[str, Any]:
    """Resolve one catalog-authorized self stage secondary without branching.

    The resolver owns no runtime state and intentionally supports only a
    catalog-defined ability-neutral set.  Unknown or unclassified authority
    cannot become a neutral secondary-effect result.
    """
    move_id = _move_id(move)
    if move_id is None:
        return _result("incomplete", "canonical_move_identity_unknown")
    rule = _rule(move_id)
    base = {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "move_id": move_id,
        "required_source_slots": ("attacker_ability",),
    }
    if rule is None:
        return {
            **base,
            "status": "unsupported",
            "reason": "move_not_in_supported_probabilistic_self_stage_catalog",
            "ledger": (_row("move_rule", "unsupported", source_value=move_id),),
        }
    metadata = _metadata(move, rule)
    if metadata["status"] != "resolved":
        return {**base, "rule_id": rule["rule_id"], **metadata}
    ability = _ability(source_authority)
    if ability is None:
        return _result("rejected", "invalid_probabilistic_self_stage_source_authority")
    resolved_base = {**base, "rule_id": rule["rule_id"]}
    if ability["status"] == "unknown":
        return {
            **resolved_base,
            "status": "incomplete",
            "reason": "attacker_ability_unknown",
            "ledger": (_row("attacker_ability", "unknown"),),
        }

    policy = rule["attacker_ability_policy"]
    ability_id = ability["value"]
    if ability_id in policy["unsupported"]:
        return {
            **resolved_base,
            "status": "unsupported",
            "reason": "attacker_ability_not_supported_for_probabilistic_self_stage_effect",
            "ledger": (_row("attacker_ability", "unsupported", source_value=ability_id),),
        }
    if ability_id in policy["suppresses"]:
        applicability = ability.get("applicability")
        if applicability is None:
            return _result("rejected", "invalid_sheer_force_applicability_authority")
        if applicability == "unknown":
            return {
                **resolved_base,
                "status": "incomplete",
                "reason": "sheer_force_applicability_unknown",
                "ledger": (_row("attacker_ability", "unknown", source_value=ability_id),),
            }
        if applicability == "applicable":
            return _resolved(rule, resolved_base, ledger=(_row("attacker_ability", "suppressed", source_value=ability_id),), suppressed=True)
        return _resolved(rule, resolved_base, ledger=(_row("attacker_ability", "known_neutral", source_value=ability_id, reason="sheer_force_proven_not_applicable"),))
    if ability_id not in policy["known_neutral"]:
        return {
            **resolved_base,
            "status": "unsupported",
            "reason": "attacker_ability_not_in_probabilistic_self_stage_neutral_catalog",
            "ledger": (_row("attacker_ability", "unsupported", source_value=ability_id),),
        }
    return _resolved(rule, resolved_base, ledger=(_row("attacker_ability", "known_neutral", source_value=ability_id, reason="catalog_known_neutral"),))


def _move_id(move: Any) -> str | None:
    value = move.get("move_id") if isinstance(move, Mapping) else None
    return value if isinstance(value, str) and value else None


def _metadata(move: Mapping[str, Any] | Any, rule: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(move, Mapping):
        return _result("incomplete", "canonical_move_metadata_unknown")
    category, power, chance, changes = move.get("category"), move.get("power"), move.get("effect_chance"), _changes(move.get("stat_changes"))
    if category not in {"physical", "special"}:
        return _result("incomplete", "canonical_move_category_unknown")
    if not isinstance(power, int) or isinstance(power, bool) or power < 1:
        return _result("incomplete", "canonical_damaging_power_unknown")
    if not isinstance(chance, int) or isinstance(chance, bool) or not 0 <= chance <= 100:
        return _result("incomplete", "canonical_effect_chance_unknown")
    if changes is None:
        return _result("incomplete", "canonical_stat_changes_unknown")
    effect = rule["effect"]
    if category != rule["category"]:
        return _result("unsupported", "catalog_metadata_category_mismatch")
    if chance != rule["effect_chance"]:
        return _result("unsupported", "catalog_metadata_effect_chance_mismatch")
    if changes != ((effect["stat"], effect["delta"]),):
        return _result("unsupported", "catalog_metadata_stat_changes_mismatch")
    return {"status": "resolved"}


def _changes(value: Any) -> tuple[tuple[str, int], ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[tuple[str, int]] = []
    for row in value:
        stat, delta = (row.get("stat"), row.get("change")) if isinstance(row, Mapping) else (None, None)
        if not isinstance(stat, str) or stat not in _STATS or not isinstance(delta, int) or isinstance(delta, bool) or not -6 <= delta <= 6 or delta == 0:
            return None
        result.append((stat, delta))
    return tuple(result)


def _ability(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return {"status": "unknown"}
    row = value.get("attacker_ability")
    if not isinstance(row, Mapping) or row.get("status") not in _ABILITY_STATUSES:
        return {"status": "unknown"} if row is None else None
    if row["status"] == "unknown":
        return {"status": "unknown"} if set(row) == {"status"} else None
    ability = row.get("value")
    if not isinstance(ability, str) or not ability:
        return None
    result: dict[str, Any] = {"status": "known", "value": ability}
    if "applicability" in row:
        value = row["applicability"]
        if not isinstance(value, Mapping) or set(value) != {"status"} or value.get("status") not in _APPLICABILITY:
            return None
        result["applicability"] = value["status"]
    return result


def _resolved(rule: Mapping[str, Any], base: Mapping[str, Any], *, ledger: tuple[dict[str, Any], ...], suppressed: bool = False) -> dict[str, Any]:
    chance = 0 if suppressed else rule["effect_chance"]
    return {
        **base,
        "status": "resolved",
        "probability": {"numerator": chance, "denominator": 100},
        "effect": deepcopy(rule["effect"]),
        "conditions": deepcopy(rule["conditions"]),
        "suppressed": suppressed,
        "ledger": deepcopy(ledger),
        "provenance": "canonical-maintained-gen9-mechanics-catalog-v1",
    }


def _rule(move_id: str) -> dict[str, Any] | None:
    try:
        data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, Mapping) or data.get("schema_version") != CATALOG_VERSION or not isinstance(data.get("rules"), list):
        return None
    matches = [item for item in data["rules"] if _valid_rule(item) and item["move_id"] == move_id]
    return deepcopy(matches[0]) if len(matches) == 1 else None


def _valid_rule(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    effect, conditions, policy = value.get("effect"), value.get("conditions"), value.get("attacker_ability_policy")
    return (
        isinstance(value.get("rule_id"), str) and bool(value["rule_id"])
        and isinstance(value.get("move_id"), str) and bool(value["move_id"])
        and value.get("category") in {"physical", "special"}
        and isinstance(value.get("effect_chance"), int) and not isinstance(value["effect_chance"], bool) and 1 <= value["effect_chance"] <= 99
        and isinstance(effect, Mapping) and effect.get("owner") == "self" and effect.get("stat") in _STATS
        and isinstance(effect.get("delta"), int) and not isinstance(effect["delta"], bool) and 1 <= effect["delta"] <= 6
        and isinstance(conditions, Mapping) and conditions == {"requires_successful_damaging_hit": True, "blocked_by_substitute": False, "target_must_survive": False}
        and isinstance(policy, Mapping) and all(isinstance(policy.get(key), list) and all(isinstance(item, str) and item for item in policy[key]) for key in ("known_neutral", "suppresses", "unsupported"))
    )


def _row(slot: str, state: str, *, source_value: str | None = None, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"slot": slot, "state": state}
    if source_value is not None:
        result["source_value"] = source_value
    if reason is not None:
        result["reason"] = reason
    return result


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
