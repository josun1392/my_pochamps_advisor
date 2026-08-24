"""Strict catalog-backed classification for target-owned status secondaries."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "probabilistic-target-status-effect-capability-resolution-v1"
CATALOG_VERSION = "probabilistic-target-status-effects-catalog-v1"
_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "probabilistic_target_status_effects.json"
_APPLICABILITY = frozenset({"applicable", "not_applicable", "unknown"})
_INTERACTION = frozenset({"affecting", "not_affecting", "unknown"})
_CONDITIONS = frozenset({"burn", "freeze", "none", "paralysis", "poison", "sleep", "toxic"})
_TYPES = frozenset({"bug", "dark", "dragon", "electric", "fairy", "fighting", "fire", "flying", "ghost", "grass", "ground", "ice", "normal", "poison", "psychic", "rock", "steel", "water"})


def resolve_probabilistic_target_status_effect_capability(*, move: Mapping[str, Any] | Any, source_authority: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Resolve one catalog-approved target status secondary without runtime or branching."""
    move_id = _move_id(move)
    if move_id is None:
        return _result("incomplete", "canonical_move_identity_unknown")
    rule = _rule(move_id)
    base = {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "move_id": move_id,
        "required_source_slots": ("target_condition", "target_types", "attacker_ability", "target_ability", "target_item"),
    }
    if rule is None:
        return {**base, "status": "unsupported", "reason": "move_not_in_supported_probabilistic_target_status_catalog", "ledger": (_row("move_rule", "unsupported", source_value=move_id),)}
    metadata = _metadata(move, rule)
    if metadata["status"] != "resolved":
        return {**base, "rule_id": rule["rule_id"], **metadata}
    source = _source(source_authority)
    if source is None:
        return _result("rejected", "invalid_probabilistic_target_status_source_authority")
    resolved_base = {**base, "rule_id": rule["rule_id"], "required_runtime_slots": tuple(rule["required_runtime_slots"])}
    entries = (
        _condition_entry(source["target_condition"]),
        _types_entry(source["target_types"], rule),
        _attacker_entry(source["attacker_ability"], rule),
        _target_ability_entry(source["target_ability"], rule),
        _target_item_entry(source["target_item"], rule),
    )
    malformed = next((entry for entry in entries if entry["state"] == "rejected"), None)
    if malformed is not None:
        return _result("rejected", malformed["reason"])
    unsupported = next((entry for entry in entries if entry["state"] == "unsupported"), None)
    if unsupported is not None:
        return {**resolved_base, "status": "unsupported", "reason": unsupported["reason"], "ledger": deepcopy(entries)}
    incomplete = next((entry for entry in entries if entry["state"] == "unknown"), None)
    if incomplete is not None:
        return {**resolved_base, "status": "incomplete", "reason": incomplete["reason"], "ledger": deepcopy(entries)}
    zero_by = tuple(entry["slot"] for entry in entries if entry["state"] in {"suppressed", "ineligible"})
    return _resolved(rule, resolved_base, ledger=entries, zero_by=zero_by)


def _move_id(move: Any) -> str | None:
    value = move.get("move_id") if isinstance(move, Mapping) else None
    return value if isinstance(value, str) and value else None


def _metadata(move: Any, rule: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(move, Mapping):
        return _result("incomplete", "canonical_move_metadata_unknown")
    category, power, target = move.get("category"), move.get("power"), move.get("target")
    chance, ailment = move.get("effect_chance"), move.get("ailment")
    if category not in {"physical", "special"}:
        return _result("incomplete", "canonical_move_category_unknown")
    if not isinstance(power, int) or isinstance(power, bool) or power < 1:
        return _result("incomplete", "canonical_damaging_power_unknown")
    if not isinstance(target, str) or not target:
        return _result("incomplete", "canonical_move_target_unknown")
    if not isinstance(chance, int) or isinstance(chance, bool) or not 0 <= chance <= 100:
        return _result("incomplete", "canonical_effect_chance_unknown")
    if not isinstance(ailment, str) or not ailment:
        return _result("incomplete", "canonical_status_ailment_unknown")
    if category != rule["category"]:
        return _result("unsupported", "catalog_metadata_category_mismatch")
    if target != rule["target_scope"]:
        return _result("unsupported", "catalog_metadata_target_mismatch")
    if chance != rule["effect_chance"]:
        return _result("unsupported", "catalog_metadata_effect_chance_mismatch")
    if ailment != rule["effect"]["condition"]:
        return _result("unsupported", "catalog_metadata_ailment_mismatch")
    return {"status": "resolved"}


def _source(value: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, Mapping):
        value = {}
    condition = _condition(value.get("target_condition"))
    types = _types(value.get("target_types"))
    attacker = _ability(value.get("attacker_ability"), applicability=True)
    target = _ability(value.get("target_ability"), interaction=True)
    item = _item(value.get("target_item"))
    if None in (condition, types, attacker, target, item):
        return None
    return {"target_condition": condition, "target_types": types, "attacker_ability": attacker, "target_ability": target, "target_item": item}


def _condition(value: Any) -> dict[str, Any] | None:
    if value is None:
        return {"status": "unknown"}
    if not isinstance(value, Mapping) or value.get("status") not in {"known_none", "known_present", "unknown"}:
        return None
    if value["status"] in {"known_none", "unknown"}:
        return {"status": value["status"]} if set(value) == {"status"} else None
    condition = value.get("condition")
    return {"status": "known_present", "condition": condition} if isinstance(condition, str) and condition in _CONDITIONS - {"none"} and set(value) == {"status", "condition"} else None


def _types(value: Any) -> dict[str, Any] | None:
    if value is None:
        return {"status": "unknown"}
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return None
    if value["status"] == "unknown":
        return {"status": "unknown"} if set(value) == {"status"} else None
    values = value.get("values")
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= 2 or any(not isinstance(item, str) or item not in _TYPES for item in values) or len(set(values)) != len(values):
        return None
    return {"status": "known", "values": tuple(values)} if set(value) == {"status", "values"} else None


def _ability(value: Any, *, applicability: bool = False, interaction: bool = False) -> dict[str, Any] | None:
    if value is None:
        return {"status": "unknown"}
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        return None
    if value["status"] == "unknown":
        return {"status": "unknown"} if set(value) == {"status"} else None
    ability = value.get("value")
    if not isinstance(ability, str) or not ability:
        return None
    result: dict[str, Any] = {"status": "known", "value": ability}
    key, allowed = ("applicability", _APPLICABILITY) if applicability else ("interaction", _INTERACTION) if interaction else (None, frozenset())
    if key is not None and key in value:
        row = value[key]
        if not isinstance(row, Mapping) or set(row) != {"status"} or row.get("status") not in allowed:
            return None
        result[key] = row["status"]
    return result


def _item(value: Any) -> dict[str, Any] | None:
    if value is None:
        return {"status": "unknown"}
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "known_absent", "unknown"}:
        return None
    status = value["status"]
    if status == "unknown":
        return {"status": "unknown"} if set(value) == {"status"} else None
    if status == "known_absent":
        return {"status": status} if set(value) == {"status"} else None
    item = value.get("value")
    return {"status": status, "value": item} if isinstance(item, str) and item and set(value) == {"status", "value"} else None


def _condition_entry(value: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("target_condition", "unknown", reason="target_current_condition_unknown")
    if value["status"] == "known_none":
        return _row("target_condition", "known_neutral", reason="target_current_condition_proven_none")
    return _row("target_condition", "ineligible", source_value=value["condition"], reason="target_current_major_condition_present")


def _types_entry(value: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("target_types", "unknown", reason="target_types_unknown")
    if set(value["values"]) & set(rule["target_type_policy"]["ineligible"]):
        return _row("target_types", "ineligible", source_value=",".join(value["values"]), reason="target_electric_type_paralysis_immunity")
    return _row("target_types", "known_neutral", source_value=",".join(value["values"]), reason="target_types_proven_status_eligible")


def _attacker_entry(value: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("attacker_ability", "unknown", reason="attacker_ability_unknown")
    ability, policy = value["value"], rule["attacker_ability_policy"]
    if ability in policy["unsupported"] or ability not in set(policy["known_neutral"]) | set(policy["suppresses"]):
        return _row("attacker_ability", "unsupported", source_value=ability, reason="attacker_ability_not_supported_for_probabilistic_target_status_effect")
    if ability != "sheer-force":
        return _row("attacker_ability", "known_neutral", source_value=ability, reason="catalog_known_neutral")
    status = value.get("applicability")
    if status is None or status == "unknown":
        return _row("attacker_ability", "unknown", source_value=ability, reason="sheer_force_applicability_unknown")
    return _row("attacker_ability", "suppressed" if status == "applicable" else "known_neutral", source_value=ability, reason="sheer_force_applicable" if status == "applicable" else "sheer_force_proven_not_applicable")


def _target_ability_entry(value: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("target_ability", "unknown", reason="target_ability_unknown")
    ability, policy = value["value"], rule["target_ability_policy"]
    if ability in policy["unsupported"] or ability not in set(policy["known_neutral"]) | set(policy["suppresses"]):
        return _row("target_ability", "unsupported", source_value=ability, reason="target_ability_not_supported_for_probabilistic_target_status_effect")
    if ability != "shield-dust":
        return _row("target_ability", "known_neutral", source_value=ability, reason="catalog_known_neutral")
    status = value.get("interaction")
    if status is None or status == "unknown":
        return _row("target_ability", "unknown", source_value=ability, reason="shield_dust_interaction_unknown")
    return _row("target_ability", "suppressed" if status == "affecting" else "known_neutral", source_value=ability, reason="shield_dust_affecting" if status == "affecting" else "shield_dust_proven_not_affecting")


def _target_item_entry(value: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("target_item", "unknown", reason="target_item_unknown")
    if value["status"] == "known_absent":
        return _row("target_item", "known_neutral", reason="target_item_proven_absent")
    item = value["value"]
    if item in rule["target_item_policy"]["suppresses"]:
        return _row("target_item", "suppressed", source_value=item, reason="covert_cloak")
    return _row("target_item", "unsupported", source_value=item, reason="target_item_not_supported_for_probabilistic_target_status_effect")


def _resolved(rule: Mapping[str, Any], base: Mapping[str, Any], *, ledger: tuple[dict[str, Any], ...], zero_by: tuple[str, ...]) -> dict[str, Any]:
    suppressed_by = tuple(entry["slot"] for entry in ledger if entry["state"] == "suppressed")
    ineligible_by = tuple(entry["slot"] for entry in ledger if entry["state"] == "ineligible")
    return {
        **base,
        "status": "resolved",
        "probability": {"numerator": 0 if zero_by else rule["effect_chance"], "denominator": 100},
        "effect": deepcopy(rule["effect"]),
        "conditions": deepcopy(rule["conditions"]),
        "suppressed": bool(suppressed_by),
        "suppressed_by": suppressed_by,
        "eligible": not ineligible_by,
        "ineligible_by": ineligible_by,
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
    rows = [row for row in data["rules"] if _valid_rule(row) and row["move_id"] == move_id]
    return deepcopy(rows[0]) if len(rows) == 1 else None


def _valid_rule(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    effect, conditions = value.get("effect"), value.get("conditions")
    policies = (value.get("attacker_ability_policy"), value.get("target_ability_policy"), value.get("target_item_policy"), value.get("target_type_policy"))
    ability_policy = lambda policy: isinstance(policy, Mapping) and all(isinstance(policy.get(key), list) and all(isinstance(item, str) and item for item in policy[key]) for key in ("known_neutral", "suppresses", "unsupported"))
    return isinstance(value.get("rule_id"), str) and bool(value["rule_id"]) and isinstance(value.get("move_id"), str) and bool(value["move_id"]) and value.get("category") in {"physical", "special"} and isinstance(value.get("target_scope"), str) and bool(value["target_scope"]) and isinstance(value.get("effect_chance"), int) and not isinstance(value["effect_chance"], bool) and 1 <= value["effect_chance"] <= 99 and isinstance(effect, Mapping) and effect == {"owner": "target", "condition": "paralysis"} and isinstance(conditions, Mapping) and conditions == {"requires_successful_damaging_hit": True, "blocked_by_substitute": True, "target_must_survive": True} and value.get("required_runtime_slots") == ["target.current_condition", "target.current_types", "attacker_ability", "target_ability", "target_item"] and value.get("suppressor_slots") == ["attacker_ability", "target_ability", "target_item"] and ability_policy(policies[0]) and ability_policy(policies[1]) and isinstance(policies[2], Mapping) and isinstance(policies[2].get("suppresses"), list) and all(isinstance(item, str) and item for item in policies[2]["suppresses"]) and isinstance(policies[3], Mapping) and policies[3].get("ineligible") == ["electric"]


def _row(slot: str, state: str, *, source_value: str | None = None, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"slot": slot, "state": state}
    if source_value is not None:
        result["source_value"] = source_value
    if reason is not None:
        result["reason"] = reason
    return result


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
