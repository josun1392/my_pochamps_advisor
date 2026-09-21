"""Canonical capability classification for non-stage hit modifiers.

This module deliberately classifies only catalog-backed capability.  It does
not calculate final accuracy or own runtime/D0 state.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.abilities import get_ability
from advisor.canonical_fling_berry_target_intrinsic_on_eat_suppression import (
    resolve_canonical_fling_berry_target_intrinsic_on_eat_suppression_contract,
    resolve_canonical_target_item_ignore_klutz,
)


SCHEMA_VERSION = "hit-modifier-capability-resolution-v1"
CATALOG_VERSION = "hit-modifier-capability-catalog-v1"
HUSTLE_RULE_ID = "hustle-physical-accuracy-penalty-v1"
_MOVE_CATEGORIES = frozenset({"physical", "special", "status"})
_SOURCE_STATUSES = frozenset({"known", "known_absent", "unknown"})
_APPLICABILITY = frozenset({"applicable", "not_applicable", "unknown"})
# These identities have maintained Gen 9 semantics, but no accuracy effect.
# Keeping this explicit is important: a known ability is not neutral merely
# because the current resolver has no rule for it.
# These held items have maintained mechanics elsewhere, but no regular-accuracy
# effect.  Every other known target item stays unsupported until catalogued.
_KNOWN_NEUTRAL_TARGET_ITEM_IDS = frozenset({
    "black-belt", "choice-scarf", "focus-sash", "life-orb", "quick-claw",
    "rocky-helmet", "sitrus-berry", "power-herb",
})

_KNOWN_NEUTRAL_ABILITY_IDS = frozenset({
    "early-bird", "own-tempo", "tangled-feet", "magician", "pickpocket", "sticky-hold", "neutralizing-gas", "pressure", "guts", "skill-link", "static", "flame-body", "poison-point", "overcoat", "insomnia", "vital-spirit",
    "tough-claws", "reckless", "punk-rock", "sharpness", "sheer-force", "mold-breaker", "rough-skin", "multiscale",
    "blaze", "torrent", "overgrow", "swarm", "analytic", "stakeout", "supreme-overlord",
    # Maintained defender mechanics that affect damage, crit, or post-hit
    # consequences but never a regular-accuracy check.
    "intimidate", "drizzle", "drought", "sand-stream", "snow-warning", "battle-armor", "shell-armor",
    "sturdy", "iron-barbs", "effect-spore", "heatproof", "water-bubble", "fluffy", "shadow-shield", "magic-guard",
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


def resolve_runtime_hit_modifier_capabilities(*, move: Mapping[str, Any], source_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Strict v2 runtime catalog including target, field, and volatile facts."""
    normalized = _move(move)
    if normalized is None or not isinstance(source_authority, Mapping):
        return _result("rejected", "invalid_hit_modifier_capability_request")
    slots = ("attacker_ability", "target_ability", "target_item", "weather", "target_confusion")
    source = {slot: _runtime_source(source_authority.get(slot)) for slot in slots}
    if any(value is None for value in source.values()):
        return _result("rejected", "invalid_runtime_hit_modifier_source_authority")
    base = {"schema_version": SCHEMA_VERSION, "catalog_version": "hit-modifier-capability-catalog-v2",
            "move_id": normalized["move_id"], "move_category": normalized["category"], "required_source_slots": slots}
    ledger: list[dict[str, Any]] = []
    weather = source["weather"]
    if normalized["move_id"] in {"thunder", "hurricane", "blizzard"}:
        if weather["status"] == "unknown": return _runtime_unavailable(base, "incomplete", "weather_unknown_for_move_accuracy", ledger, "weather")
        weather_accuracy = {
            "thunder": {"rain": 100, "sun": 50},
            "hurricane": {"rain": 100, "sun": 50},
            "blizzard": {"snow": 100},
        }
        override = weather_accuracy[normalized["move_id"]].get(weather["value"])
        if override is not None:
            ledger.append(_row("weather", "applicable", rule_id=f"{normalized['move_id']}-weather-accuracy-v1", effect={"kind": "base_accuracy_override", "value": override, "ordering": "before_accuracy_multipliers"}))
        elif weather["value"] in {"none", "rain", "snow", "sun", "sandstorm"}:
            ledger.append(_row("weather", "known_neutral", source_value=weather["value"], reason="catalog_weather_condition_not_met"))
        else: return _runtime_unavailable(base, "unsupported", "weather_not_in_supported_hit_modifier_catalog", ledger, "weather", weather["value"])
    else: ledger.append(_row("weather", "not_applicable", reason="move_has_no_catalogued_weather_accuracy_rule"))
    attacker = source["attacker_ability"]
    if attacker["status"] == "unknown": return _runtime_unavailable(base, "incomplete", "attacker_ability_unknown", ledger, "attacker_ability")
    if attacker["status"] == "known" and attacker["value"] == "compound-eyes": return _runtime_unavailable(base, "unsupported", "attacker_ability_not_in_supported_hit_modifier_catalog", ledger, "attacker_ability", "compound-eyes")
    # Preserve the original strict applicability record for the established
    # Hustle owner.  ``_runtime_source`` intentionally reduces it to a small
    # catalog view, but the v1 owner validates the nested authority shape.
    old = resolve_hit_modifier_capabilities(
        move=normalized,
        source_authority={"attacker_ability": source_authority["attacker_ability"]},
    )
    if old["status"] != "resolved": return {**base, "status": old["status"], "reason": old.get("reason"), "ledger": tuple(ledger) + tuple(old.get("ledger", ()))}
    ledger.extend(old["ledger"])
    ability = source["target_ability"]
    target_klutz_fling = (
        normalized["move_id"] == "fling"
        and ability["status"] == "known"
        and ability.get("value") == "klutz"
        and resolve_canonical_fling_berry_target_intrinsic_on_eat_suppression_contract().get("status")
        == "resolved"
    )
    if ability["status"] == "unknown": return _runtime_unavailable(base, "incomplete", "target_ability_unknown", ledger, "target_ability")
    if ability["status"] == "known" and ability["value"] in {"sand-veil", "snow-cloak", "tangled-feet"}:
        if ability.get("applicability") == "unknown": return _runtime_unavailable(base, "incomplete", "target_ability_applicability_unknown", ledger, "target_ability", ability["value"])
        if ability.get("applicability") not in {"applicable", "not_applicable"}: return _result("rejected", "invalid_target_ability_applicability")
        required_weather = {"sand-veil": "sandstorm", "snow-cloak": "snow"}.get(ability["value"])
        if required_weather and weather["status"] == "unknown": return _runtime_unavailable(base, "incomplete", "weather_unknown_for_target_ability", ledger, "weather")
        if ability["value"] == "tangled-feet" and source["target_confusion"]["status"] == "unknown": return _runtime_unavailable(base, "incomplete", "target_confusion_unknown_for_tangled_feet", ledger, "target_confusion")
        applies = ability["applicability"] == "applicable" and ((required_weather and weather["value"] == required_weather) or (ability["value"] == "tangled-feet" and source["target_confusion"].get("value") == "confused"))
        if applies: ledger.append(_row("target_ability", "applicable", rule_id=f"{ability['value']}-accuracy-evasion-v1", source_value=ability["value"], effect={"kind": "accuracy_multiplier_q12", "numerator": 2048 if ability["value"] == "tangled-feet" else 3277, "denominator": 4096, "ordering": "before_accuracy_evasion_stages"}))
        else: ledger.append(_row("target_ability", "known_neutral", source_value=ability["value"], reason="catalog_ability_condition_not_met"))
    elif ability["status"] == "known_absent" or ability.get("value") in _KNOWN_NEUTRAL_ABILITY_IDS | {"hustle"} or target_klutz_fling:
        ledger.append(_row("target_ability", "known_neutral", **({"source_value": ability["value"]} if ability["status"] == "known" else {"reason": "proven_ability_absent"})))
    else: return _runtime_unavailable(base, "unsupported", "target_ability_not_in_supported_hit_modifier_catalog", ledger, "target_ability", ability.get("value"))
    item = source["target_item"]
    if target_klutz_fling:
        if item["status"] == "unknown":
            return _runtime_unavailable(
                base, "incomplete", "target_klutz_current_held_item_unknown",
                ledger, "target_item",
            )
        if item["status"] == "known_absent":
            ledger.append(_row(
                "target_item", "known_neutral",
                reason="target_klutz_known_absent_item_suppresses_no_accuracy_effect",
            ))
        elif item["status"] == "known":
            classification = resolve_canonical_target_item_ignore_klutz(item["value"])
            if classification.get("status") != "resolved":
                return _runtime_unavailable(
                    base, "incomplete",
                    classification.get("reason", "target_klutz_item_ignore_klutz_unavailable"),
                    ledger, "target_item", item["value"],
                )
            if classification.get("ignore_klutz") is False:
                ledger.append(_row(
                    "target_item", "known_neutral", source_value=item["value"],
                    reason="target_klutz_suppresses_current_item_accuracy_effect",
                ))
            elif classification.get("showdown_item_id") == "abilityshield":
                ledger.append(_row(
                    "target_item", "known_neutral", source_value=item["value"],
                    reason="ability_shield_has_no_regular_accuracy_effect",
                ))
            else:
                return _runtime_unavailable(
                    base, "unsupported",
                    "target_ignore_klutz_item_not_in_supported_hit_modifier_catalog",
                    ledger, "target_item", item["value"],
                )
        else:
            return _result("rejected", "invalid_target_klutz_item_authority")
    elif item["status"] == "unknown": return _runtime_unavailable(base, "incomplete", "target_item_unknown", ledger, "target_item")
    elif item["status"] == "known" and item["value"] == "bright-powder":
        if item.get("applicability") == "unknown": return _runtime_unavailable(base, "incomplete", "target_item_applicability_unknown", ledger, "target_item", "bright-powder")
        if item.get("applicability") not in {"applicable", "not_applicable"}: return _result("rejected", "invalid_target_item_applicability")
        if item["applicability"] == "applicable": ledger.append(_row("target_item", "applicable", rule_id="bright-powder-evasion-v1", source_value="bright-powder", effect={"kind": "accuracy_multiplier_q12", "numerator": 3686, "denominator": 4096, "ordering": "before_accuracy_evasion_stages"}))
        else: ledger.append(_row("target_item", "known_neutral", rule_id="bright-powder-evasion-v1", source_value="bright-powder", reason="bright_powder_proven_suppressed"))
    elif item["status"] == "known_absent": ledger.append(_row("target_item", "known_neutral", reason="proven_item_absent"))
    elif item["status"] == "known" and item["value"] in _KNOWN_NEUTRAL_TARGET_ITEM_IDS: ledger.append(_row("target_item", "known_neutral", source_value=item["value"], reason="catalog_known_no_accuracy_effect"))
    else: return _runtime_unavailable(base, "unsupported", "target_item_not_in_supported_hit_modifier_catalog", ledger, "target_item", item.get("value"))
    ledger.append(_row("target_confusion", "not_applicable", reason="target_ability_has_no_confusion_accuracy_rule") if ability.get("value") != "tangled-feet" else _row("target_confusion", "known_neutral", reason="catalog_confusion_condition_not_met"))
    return {**base, "status": "resolved", "ledger": tuple(ledger)}


def _runtime_source(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "known_absent", "unknown"}: return None
    if value["status"] != "known": return {"status": value["status"]} if set(value) == {"status"} else None
    if not isinstance(value.get("value"), str) or not value["value"]: return None
    result = {"status": "known", "value": value["value"]}
    if "applicability" in value:
        app = value["applicability"]
        if not isinstance(app, Mapping) or set(app) != {"status"} or app.get("status") not in _APPLICABILITY: return None
        result["applicability"] = app["status"]
    return result


def _runtime_unavailable(base: Mapping[str, Any], status: str, reason: str, ledger: list[dict[str, Any]], slot: str, source_value: str | None = None) -> dict[str, Any]:
    return {**base, "status": status, "reason": reason, "ledger": tuple(ledger + [_row(slot, "unknown" if status == "incomplete" else "unsupported", source_value=source_value)])}
