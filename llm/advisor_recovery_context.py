"""Limited recovery context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any


RECOVERY_CONTEXT_MODE = "limited_item_recovery_context"
SUPPORTED_RECOVERY_ITEMS = {"sitrus-berry", "leftovers"}
RECOVERY_LIMITATIONS = {
    "sitrus-berry": [
        "Limited recovery context only.",
        "Exact activation threshold, item consumption, switching, residual damage, and turn sequencing are not modeled.",
    ],
    "leftovers": [
        "Limited end-of-turn recovery context only.",
        "Turn order, switching, protection, residual damage, and exact turn sequencing are not modeled.",
    ],
}


def build_recovery_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    *,
    defender_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": RECOVERY_CONTEXT_MODE,
        "scope": scope,
        "defender_side": defender_key,
        "is_final_battle_truth": False,
    }

    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")

    item_profile = _item_profile(battle_input, defender_key)
    item_status = item_profile.get("status")
    item_id = item_profile.get("item_id")
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_recovery_item")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id not in SUPPORTED_RECOVERY_ITEMS:
        return _unavailable(base, "no_recovery_item")

    max_hp = _defender_max_hp(battle_input, damage_estimate, defender_key)
    if max_hp is None:
        return _unavailable(base, "defender_max_hp_missing")

    return {
        **base,
        "available": True,
        "item": {
            "item_id": item_id,
            "status": "user_confirmed",
        },
        "recovery_effect": _recovery_effect(item_id, max_hp),
        "limitations": list(RECOVERY_LIMITATIONS[item_id]),
    }


def _unavailable(base: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **base,
        "available": False,
        "reason": reason,
    }


def _damage_estimate_available(damage_estimate: dict[str, Any]) -> bool:
    if not isinstance(damage_estimate, dict):
        return False
    if damage_estimate.get("status") != "available_with_default_assumptions":
        return False
    return isinstance(damage_estimate.get("damage_range"), dict)


def _recovery_effect(item_id: str, max_hp: int) -> dict[str, Any]:
    if item_id == "sitrus-berry":
        return {
            "type": "sitrus_berry",
            "timing": "threshold_or_after_damage_limited",
            "estimated_recovery_hp": max_hp // 4,
            "formula_label": "floor(max_hp / 4)",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
        }
    return {
        "type": "leftovers",
        "timing": "end_of_turn_limited",
        "estimated_recovery_hp": max_hp // 16,
        "formula_label": "floor(max_hp / 16)",
        "raw_damage_rolls_changed": False,
        "ko_context_changed": False,
    }


def _item_profile(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    item_profiles = battle_input.get("item_profiles")
    if not isinstance(item_profiles, dict):
        return {}
    profile = item_profiles.get(role_key)
    return profile if isinstance(profile, dict) else {}


def _defender_max_hp(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    defender_key: str,
) -> int | None:
    defender = _pokemon_payload(battle_input, defender_key)
    max_hp = _positive_int(defender.get("max_hp"))
    if max_hp is not None:
        return max_hp

    stat_profiles = battle_input.get("stat_profiles")
    if isinstance(stat_profiles, dict):
        profile = stat_profiles.get(defender_key)
        if isinstance(profile, dict):
            final_stats = profile.get("final_stats")
            if isinstance(final_stats, dict):
                stat_hp = _positive_int(final_stats.get("hp"))
                if stat_hp is not None:
                    return stat_hp

    derived_stats = damage_estimate.get("derived_stats")
    if isinstance(derived_stats, dict):
        defender_stats = derived_stats.get("defender")
        if isinstance(defender_stats, dict):
            return _positive_int(defender_stats.get("default_max_hp"))

    return None


def _pokemon_payload(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    pokemon = battle_input.get("pokemon")
    if not isinstance(pokemon, dict):
        return {}
    payload = pokemon.get(role_key)
    return payload if isinstance(payload, dict) else {}


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None
