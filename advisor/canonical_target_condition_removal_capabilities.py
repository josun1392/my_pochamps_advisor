"""Strict catalog classification for deterministic target condition removal."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "canonical-target-condition-removal-capability-resolution-v1"
_CATALOG = Path(__file__).resolve().parents[1] / "data" / "static" / "canonical_target_condition_removal_effects.json"


def resolve_canonical_target_condition_removal_capability(*, move: Mapping[str, Any] | Any, target_condition_authority: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Resolve only an exact catalogued pre-hit target-condition effect."""
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(move_id, str) or not move_id:
        return _result("incomplete", "canonical_move_identity_unknown", base)
    rule = next((row for row in _rules() if row.get("move_id") == move_id), None)
    if not isinstance(rule, Mapping):
        return _result("unsupported", "move_not_in_supported_target_condition_removal_catalog", base)
    if not isinstance(move, Mapping):
        return _result("incomplete", "canonical_move_metadata_unknown", base)
    for key in ("category", "type", "power", "accuracy", "target", "effect_chance", "ailment"):
        expected = rule["target_scope"] if key == "target" else rule[key]
        if move.get(key) != expected:
            return _result("unsupported", f"catalog_metadata_{key}_mismatch", base)
    condition = _condition(target_condition_authority)
    if isinstance(condition, Mapping):
        return _result("incomplete", condition["reason"], base)
    effect = deepcopy(dict(rule["effect"]))
    return {
        **base, "status": "resolved", "rule_id": rule["rule_id"],
        "effect": effect, "conditions": deepcopy(dict(rule["conditions"])),
        "target_condition_before": deepcopy(dict(target_condition_authority["condition"])),
        "effect_applicable": condition == effect["condition_before"],
        "provenance": "canonical_sparkling_aria_burn_clearing_catalog_v1",
    }


def _condition(value: Any) -> str | dict[str, str]:
    if not isinstance(value, Mapping) or value.get("status") != "resolved":
        return {"reason": "target_current_condition_authority_unavailable"}
    condition = value.get("condition")
    if not isinstance(condition, Mapping):
        return {"reason": "target_current_condition_authority_invalid"}
    if condition.get("status") == "known_none":
        return "none"
    if condition.get("status") == "known_present" and condition.get("condition") in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}:
        return condition["condition"]
    return {"reason": "target_current_condition_unknown"}


def _rules() -> tuple[Mapping[str, Any], ...]:
    try:
        raw = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    rules = raw.get("rules") if isinstance(raw, Mapping) else None
    return tuple(row for row in rules if isinstance(row, Mapping)) if isinstance(rules, list) else ()


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {**base, "status": status, "reason": reason}
