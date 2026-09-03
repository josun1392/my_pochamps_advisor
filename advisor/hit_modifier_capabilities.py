"""Canonical capability classification for non-stage hit modifiers.

This module deliberately classifies only catalog-backed capability.  It does
not calculate final accuracy or own runtime/D0 state.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.abilities import get_ability


SCHEMA_VERSION = "hit-modifier-capability-resolution-v1"
CATALOG_VERSION = "hit-modifier-capability-catalog-v1"
HUSTLE_RULE_ID = "hustle-physical-accuracy-penalty-v1"
_MOVE_CATEGORIES = frozenset({"physical", "special", "status"})
_SOURCE_STATUSES = frozenset({"known", "known_absent", "unknown"})
_APPLICABILITY = frozenset({"applicable", "not_applicable", "unknown"})
# These identities have maintained Gen 9 semantics, but no accuracy effect.
# Keeping this explicit is important: a known ability is not neutral merely
# because the current resolver has no rule for it.
_KNOWN_NEUTRAL_ABILITY_IDS = frozenset({
    "pressure", "guts", "skill-link", "static", "flame-body", "poison-point", "overcoat", "insomnia", "vital-spirit",
    "tough-claws", "reckless", "punk-rock", "sharpness", "sheer-force", "mold-breaker",
    "blaze", "torrent", "overgrow", "swarm", "analytic", "stakeout", "supreme-overlord",
})


def resolve_hit_modifier_capabilities(*, move: Mapping[str, Any], source_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Classify the supported Hustle accuracy rule from detached exact facts.

    Only ``attacker_ability`` is relevant to this v1 rule family.  Known
    identities outside this catalog are intentionally unsupported, never
    inferred neutral.
    """
    normalized_move = _move(move)
    if normalized_move is None or not isinstance(source_authority, Mapping):
        return _result("rejected", "invalid_hit_modifier_capability_request")
    ability = _source(source_authority.get("attacker_ability"))
    if ability is None:
        return _result("rejected", "invalid_attacker_ability_authority")
    base = {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "move_id": normalized_move["move_id"],
        "move_category": normalized_move["category"],
        "required_source_slots": ("attacker_ability",),
    }
    if ability["status"] == "unknown":
        return {**base, "status": "incomplete", "reason": "attacker_ability_unknown", "ledger": (_row("attacker_ability", "unknown"),)}
    if ability["status"] == "known_absent":
        return {**base, "status": "resolved", "ledger": (_row("attacker_ability", "known_neutral", reason="proven_ability_absent"),)}
    ability_id = ability["value"]
    if ability_id in _KNOWN_NEUTRAL_ABILITY_IDS:
        return {**base, "status": "resolved", "ledger": (_row("attacker_ability", "known_neutral", source_value=ability_id, reason="catalog_known_no_accuracy_effect"),)}
    if ability_id != "hustle":
        return {**base, "status": "unsupported", "reason": "attacker_ability_not_in_supported_hit_modifier_catalog", "ledger": (_row("attacker_ability", "unsupported", source_value=ability_id),)}
    if normalized_move["category"] != "physical":
        return {**base, "status": "resolved", "ledger": (_row("attacker_ability", "known_neutral", rule_id=HUSTLE_RULE_ID, reason="hustle_condition_not_met"),)}
    applicability = _applicability(ability.get("applicability"))
    if applicability is None:
        return _result("rejected", "invalid_attacker_ability_applicability")
    if applicability == "unknown":
        return {**base, "status": "incomplete", "reason": "hustle_applicability_unknown", "ledger": (_row("attacker_ability", "unknown", rule_id=HUSTLE_RULE_ID),)}
    if applicability == "not_applicable":
        return {**base, "status": "resolved", "ledger": (_row("attacker_ability", "known_neutral", rule_id=HUSTLE_RULE_ID, reason="hustle_proven_not_applicable"),)}
    factor = _hustle_factor()
    if factor is None:
        return {**base, "status": "unsupported", "reason": "hustle_catalog_rule_unavailable", "ledger": (_row("attacker_ability", "unsupported", rule_id=HUSTLE_RULE_ID),)}
    return {**base, "status": "resolved", "ledger": (_row("attacker_ability", "applicable", rule_id=HUSTLE_RULE_ID, effect={"kind": "accuracy_multiplier_q12", **factor, "ordering": "before_accuracy_evasion_stages"}),)}


def _move(value: Any) -> dict[str, str] | None:
    if not isinstance(value, Mapping): return None
    move_id, category = value.get("move_id"), value.get("category")
    if not isinstance(move_id, str) or not move_id or category not in _MOVE_CATEGORIES: return None
    return {"move_id": move_id, "category": category}


def _source(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") not in _SOURCE_STATUSES: return None
    status = value["status"]
    if status == "known":
        known = value.get("value")
        if not isinstance(known, str) or not known: return None
        return {"status": status, "value": known, **({"applicability": deepcopy(value["applicability"])} if "applicability" in value else {})}
    if set(value) != {"status"}: return None
    return {"status": status}


def _applicability(value: Any) -> str | None:
    if not isinstance(value, Mapping) or set(value) != {"status"} or value.get("status") not in _APPLICABILITY: return None
    return value["status"]


def _hustle_factor() -> dict[str, int] | None:
    ability = get_ability("hustle")
    raw = ability.raw_data if ability is not None else None
    value = raw.get("accuracy_penalty_q12") if isinstance(raw, Mapping) else None
    if not ability or not ability.implemented or raw.get("condition") != "physical_move" or not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return None
    return {"numerator": value, "denominator": 4096}


def _row(slot: str, state: str, *, rule_id: str | None = None, reason: str | None = None, source_value: str | None = None, effect: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"slot": slot, "state": state}
    if rule_id is not None: row["rule_id"] = rule_id
    if reason is not None: row["reason"] = reason
    if source_value is not None: row["source_value"] = source_value
    if effect is not None: row["effect"] = deepcopy(dict(effect))
    return row


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
