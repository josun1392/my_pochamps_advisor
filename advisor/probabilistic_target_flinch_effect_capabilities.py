"""Strict catalog authority for bounded target flinch secondaries."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "probabilistic-target-flinch-effect-capability-resolution-v1"
_CATALOG = Path(__file__).resolve().parents[1] / "data" / "static" / "probabilistic_target_flinch_effects.json"


def resolve_probabilistic_target_flinch_effect_capability(*, move: Mapping[str, Any] | Any, source_authority: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Resolve only exact catalog metadata; modifiers are deliberately absent."""
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    if not isinstance(move_id, str) or not move_id:
        return _result("incomplete", "canonical_move_identity_unknown")
    rule = next((row for row in _rules() if row.get("move_id") == move_id), None)
    base = {"schema_version": SCHEMA_VERSION, "move_id": move_id}
    if not isinstance(rule, Mapping):
        return {**base, "status": "unsupported", "reason": "move_not_in_supported_probabilistic_target_flinch_catalog"}
    if not isinstance(move, Mapping):
        return {**base, "status": "incomplete", "reason": "canonical_move_metadata_unknown"}
    if not isinstance(move.get("power"), int) or isinstance(move.get("power"), bool) or move["power"] <= 0:
        return {**base, "status": "incomplete", "reason": "canonical_damaging_power_unknown"}
    if move.get("category") != rule["category"] or move.get("target") != rule["target_scope"]:
        return {**base, "status": "unsupported", "reason": "catalog_metadata_category_or_target_mismatch"}
    if move.get("effect_chance") != rule["effect_chance"]:
        return {**base, "status": "unsupported", "reason": "catalog_metadata_effect_chance_mismatch"}
    if move.get("ailment") != "flinch":
        return {**base, "status": "unsupported", "reason": "catalog_metadata_flinch_ailment_mismatch"}
    source = source_authority if isinstance(source_authority, Mapping) else {}
    attacker, target, item = source.get("attacker_ability"), source.get("target_ability"), source.get("target_item")
    if not all(isinstance(row, Mapping) for row in (attacker, target, item)):
        return {**base, "status": "rejected", "reason": "invalid_target_flinch_source_authority"}
    if attacker.get("status") == "unknown" or target.get("status") == "unknown" or item.get("status") == "unknown":
        return {**base, "status": "incomplete", "reason": "target_flinch_modifier_authority_unknown"}
    if attacker.get("value") == "serene-grace" or target.get("value") == "shield-dust" or item.get("value") == "covert-cloak":
        return {**base, "status": "unsupported", "reason": "target_flinch_modifier_requires_separate_authority"}
    if attacker.get("status") not in {"known", "known_absent"} or target.get("status") not in {"known", "known_absent"} or item.get("status") not in {"known", "known_absent"}:
        return {**base, "status": "rejected", "reason": "invalid_target_flinch_source_authority"}
    return {
        **base, "status": "resolved", "rule_id": rule["rule_id"],
        "probability": {"numerator": rule["effect_chance"], "denominator": 100},
        "effect": deepcopy(rule["effect"]), "conditions": deepcopy(rule["conditions"]),
        "provenance": "canonical_iron_head_flinch_catalog_v1",
    }


def _rules() -> tuple[Mapping[str, Any], ...]:
    try:
        raw = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    values = raw.get("rules") if isinstance(raw, Mapping) else None
    return tuple(row for row in values if isinstance(row, Mapping)) if isinstance(values, list) else ()


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
