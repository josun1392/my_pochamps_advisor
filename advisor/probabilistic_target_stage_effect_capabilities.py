"""Strict catalog-backed classification for target-owned stage secondaries."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "probabilistic-target-stage-effect-capability-resolution-v1"
CATALOG_VERSION = "probabilistic-target-stage-effects-catalog-v1"
_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "static" / "probabilistic_target_stage_effects.json"
_STATS = frozenset({"attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"})
_APPLICABILITY = frozenset({"applicable", "not_applicable", "unknown"})
_INTERACTION = frozenset({"affecting", "not_affecting", "unknown"})


def resolve_probabilistic_target_stage_effect_capability(*, move: Mapping[str, Any] | Any, source_authority: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Resolve one catalog-approved target secondary without runtime or branching."""
    move_id = _move_id(move)
    if move_id is None:
        return _result("incomplete", "canonical_move_identity_unknown")
    rule = _rule(move_id)
    base = {
        "schema_version": SCHEMA_VERSION, "catalog_version": CATALOG_VERSION, "move_id": move_id,
        "required_source_slots": ("attacker_ability", "target_ability", "target_item"),
    }
    if rule is None:
        return {**base, "status": "unsupported", "reason": "move_not_in_supported_probabilistic_target_stage_catalog", "ledger": (_row("move_rule", "unsupported", source_value=move_id),)}
    metadata = _metadata(move, rule)
    if metadata["status"] != "resolved":
        return {**base, "rule_id": rule["rule_id"], **metadata}
    source = _source(source_authority)
    if source is None:
        return _result("rejected", "invalid_probabilistic_target_stage_source_authority")
    resolved_base = {**base, "rule_id": rule["rule_id"], "required_runtime_slots": tuple(rule["required_runtime_slots"])}
    entries = (
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
    suppressors = tuple(entry["slot"] for entry in entries if entry["state"] == "suppressed")
    return _resolved(rule, resolved_base, ledger=entries, suppressed_by=suppressors)


def _move_id(move: Any) -> str | None:
    value = move.get("move_id") if isinstance(move, Mapping) else None
    return value if isinstance(value, str) and value else None


def _metadata(move: Any, rule: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(move, Mapping):
        return _result("incomplete", "canonical_move_metadata_unknown")
    category, power, target = move.get("category"), move.get("power"), move.get("target")
    chance, changes = move.get("effect_chance"), _changes(move.get("stat_changes"))
    if category not in {"physical", "special"}:
        return _result("incomplete", "canonical_move_category_unknown")
    if not isinstance(power, int) or isinstance(power, bool) or power < 1:
        return _result("incomplete", "canonical_damaging_power_unknown")
    if not isinstance(target, str) or not target:
        return _result("incomplete", "canonical_move_target_unknown")
    if not isinstance(chance, int) or isinstance(chance, bool) or not 0 <= chance <= 100:
        return _result("incomplete", "canonical_effect_chance_unknown")
    if changes is None:
        return _result("incomplete", "canonical_stat_changes_unknown")
    effect = rule["effect"]
    if category != rule["category"]:
        return _result("unsupported", "catalog_metadata_category_mismatch")
    if target != rule["target_scope"]:
        return _result("unsupported", "catalog_metadata_target_mismatch")
    if chance != rule["effect_chance"]:
        return _result("unsupported", "catalog_metadata_effect_chance_mismatch")
    if changes != ((effect["stat"], effect["delta"]),):
        return _result("unsupported", "catalog_metadata_stat_changes_mismatch")
    return {"status": "resolved"}


def _changes(value: Any) -> tuple[tuple[str, int], ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    rows = []
    for row in value:
        stat, delta = (row.get("stat"), row.get("change")) if isinstance(row, Mapping) else (None, None)
        if not isinstance(stat, str) or stat not in _STATS or not isinstance(delta, int) or isinstance(delta, bool) or not -6 <= delta <= 6 or delta == 0:
            return None
        rows.append((stat, delta))
    return tuple(rows)


def _source(value: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, Mapping):
        value = {}
    attacker = _ability(value.get("attacker_ability"), applicability=True)
    target = _ability(value.get("target_ability"), interaction=True)
    item = _item(value.get("target_item"))
    return None if attacker is None or target is None or item is None else {"attacker_ability": attacker, "target_ability": target, "target_item": item}


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


def _attacker_entry(value: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("attacker_ability", "unknown", reason="attacker_ability_unknown")
    ability, policy = value["value"], rule["attacker_ability_policy"]
    if ability in policy["unsupported"] or ability not in set(policy["known_neutral"]) | set(policy["suppresses"]):
        return _row("attacker_ability", "unsupported", source_value=ability, reason="attacker_ability_not_supported_for_probabilistic_target_stage_effect")
    if ability != "sheer-force":
        return _row("attacker_ability", "known_neutral", source_value=ability, reason="catalog_known_neutral")
    status = value.get("applicability")
    if status is None:
        return _row("attacker_ability", "unknown", source_value=ability, reason="sheer_force_applicability_unknown")
    if status == "unknown":
        return _row("attacker_ability", "unknown", source_value=ability, reason="sheer_force_applicability_unknown")
    return _row("attacker_ability", "suppressed" if status == "applicable" else "known_neutral", source_value=ability, reason="sheer_force_applicable" if status == "applicable" else "sheer_force_proven_not_applicable")


def _target_ability_entry(value: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    if value["status"] == "unknown":
        return _row("target_ability", "unknown", reason="target_ability_unknown")
    ability, policy = value["value"], rule["target_ability_policy"]
    if ability in policy["unsupported"] or ability not in set(policy["known_neutral"]) | set(policy["suppresses"]):
        return _row("target_ability", "unsupported", source_value=ability, reason="target_ability_not_supported_for_probabilistic_target_stage_effect")
    if ability != "shield-dust":
        return _row("target_ability", "known_neutral", source_value=ability, reason="catalog_known_neutral")
    status = value.get("interaction")
    if status is None:
        return _row("target_ability", "unknown", source_value=ability, reason="shield_dust_interaction_unknown")
    if status == "unknown":
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
    return _row("target_item", "unsupported", source_value=item, reason="target_item_not_supported_for_probabilistic_target_stage_effect")


def _resolved(rule: Mapping[str, Any], base: Mapping[str, Any], *, ledger: tuple[dict[str, Any], ...], suppressed_by: tuple[str, ...]) -> dict[str, Any]:
    return {
        **base, "status": "resolved", "probability": {"numerator": 0 if suppressed_by else rule["effect_chance"], "denominator": 100},
        "effect": deepcopy(rule["effect"]), "conditions": deepcopy(rule["conditions"]), "suppressed": bool(suppressed_by),
        "suppressed_by": suppressed_by, "ledger": deepcopy(ledger), "provenance": "canonical-maintained-gen9-mechanics-catalog-v1",
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
    policies = (value.get("attacker_ability_policy"), value.get("target_ability_policy"), value.get("target_item_policy"))
    ability_policy = lambda policy: isinstance(policy, Mapping) and all(isinstance(policy.get(key), list) and all(isinstance(item, str) and item for item in policy[key]) for key in ("known_neutral", "suppresses", "unsupported"))
    return isinstance(value.get("rule_id"), str) and bool(value["rule_id"]) and isinstance(value.get("move_id"), str) and bool(value["move_id"]) and value.get("category") in {"physical", "special"} and isinstance(value.get("target_scope"), str) and bool(value["target_scope"]) and isinstance(value.get("effect_chance"), int) and not isinstance(value["effect_chance"], bool) and 1 <= value["effect_chance"] <= 99 and isinstance(effect, Mapping) and effect.get("owner") == "target" and effect.get("stat") in _STATS and isinstance(effect.get("delta"), int) and not isinstance(effect["delta"], bool) and -6 <= effect["delta"] <= -1 and isinstance(conditions, Mapping) and conditions == {"requires_successful_damaging_hit": True, "blocked_by_substitute": True, "target_must_survive": True} and isinstance(value.get("required_runtime_slots"), list) and value["required_runtime_slots"] == [f"target.{effect['stat']}"] and value.get("suppressor_slots") == ["attacker_ability", "target_ability", "target_item"] and ability_policy(policies[0]) and ability_policy(policies[1]) and isinstance(policies[2], Mapping) and isinstance(policies[2].get("suppresses"), list) and all(isinstance(item, str) and item for item in policies[2]["suppresses"])


def _row(slot: str, state: str, *, source_value: str | None = None, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"slot": slot, "state": state}
    if source_value is not None:
        result["source_value"] = source_value
    if reason is not None:
        result["reason"] = reason
    return result


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
