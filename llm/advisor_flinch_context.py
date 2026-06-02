"""Limited flinch context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any


FLINCH_CONTEXT_MODE = "limited_flinch_context"
KINGS_ROCK_ITEM_ID = "kings-rock"
KINGS_ROCK_LIMITATIONS = [
    "Limited flinch context only.",
    "Final flinch probability, speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled.",
]


def build_flinch_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    *,
    attacker_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": FLINCH_CONTEXT_MODE,
        "scope": scope,
        "attacker_side": attacker_key,
        "is_final_battle_truth": False,
    }

    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")

    item_profile = _item_profile(battle_input, attacker_key)
    item_status = item_profile.get("status")
    item_id = _normalized_item_id(item_profile.get("item_id"))
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_kings_rock")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != KINGS_ROCK_ITEM_ID:
        return _unavailable(base, "no_kings_rock")

    return {
        **base,
        "available": True,
        "item": {
            "item_id": KINGS_ROCK_ITEM_ID,
            "status": "user_confirmed",
        },
        "flinch_effect": {
            "type": "kings_rock",
            "effect_label": "may_add_flinch_pressure",
            "formula_label": "kings_rock_limited_flinch_modifier",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "flinch_probability_integrated": False,
            "turn_outcome_integrated": False,
        },
        "limitations": list(KINGS_ROCK_LIMITATIONS),
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


def _item_profile(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    item_profiles = battle_input.get("item_profiles")
    if not isinstance(item_profiles, dict):
        return {}
    profile = item_profiles.get(role_key)
    return profile if isinstance(profile, dict) else {}


def _normalized_item_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.lower()
