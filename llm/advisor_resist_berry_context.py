"""Limited type-resist berry context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from advisor.damage.items import ItemEffect, get_item
from llm.advisor_item_legal_gate import legal_item_context_block_reason


RESIST_BERRY_CONTEXT_MODE = "limited_resist_berry_context"
RESIST_BERRY_LIMITATIONS = [
    "Limited resist berry context only.",
    "Raw damage and KO estimates do not include berry reduction.",
    "Item consumption, multi-hit handling, abilities, weather, Tera, and turn sequencing are not modeled.",
]


def build_resist_berry_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    defender_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": RESIST_BERRY_CONTEXT_MODE,
        "scope": scope,
        "defender_side": defender_key,
        "is_final_battle_truth": False,
    }

    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")

    item_profile = _item_profile(battle_input, defender_key)
    item_status = item_profile.get("status")
    item_id = _normalized_item_id(item_profile.get("item_id"))
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_resist_berry")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")

    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    item_effect = get_item(item_id)
    if item_effect is None or item_effect.kind != "type_resist_berry":
        return _unavailable(base, "no_resist_berry")
    if item_effect.always_resist:
        return _unavailable(base, "chilan_berry_deferred")

    berry_type = _berry_type(item_effect)
    if berry_type is None:
        return _unavailable(base, "berry_type_missing")

    incoming_move_type = _move_type(move)
    if incoming_move_type is None:
        return _unavailable(base, "incoming_move_type_missing")

    type_matchup = _type_matchup(damage_estimate)
    if type_matchup is None:
        return _unavailable(base, "type_matchup_unknown")

    if incoming_move_type != berry_type or not _is_super_effective(type_matchup):
        return _unavailable(base, "move_not_super_effective")

    return {
        **base,
        "available": True,
        "item": {
            "item_id": item_id,
            "status": "user_confirmed",
            "legal_status": "legal_modeled",
        },
        "resist_effect": {
            "berry_type": berry_type,
            "incoming_move_type": incoming_move_type,
            "requires_super_effective_hit": True,
            "super_effective_match": True,
            "effect_label": "may_reduce_qualifying_super_effective_hit",
            "formula_label": "resist_berry_limited_damage_reduction",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "berry_adjusted_damage_integrated": False,
            "berry_adjusted_ko_integrated": False,
            "item_consumption_tracked": False,
        },
        "limitations": list(RESIST_BERRY_LIMITATIONS),
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
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _berry_type(item_effect: ItemEffect) -> str | None:
    if not item_effect.boosted_types:
        return None
    berry_type = item_effect.boosted_types[0]
    return berry_type if isinstance(berry_type, str) and berry_type else None


def _move_type(move: dict[str, Any] | None) -> str | None:
    if not isinstance(move, dict):
        return None
    move_type = move.get("type") or move.get("type_en")
    if not isinstance(move_type, str) or not move_type.strip():
        return None
    return move_type.strip().lower()


def _type_matchup(damage_estimate: dict[str, Any]) -> dict[str, Any] | None:
    matchup = damage_estimate.get("type_effectiveness")
    return matchup if isinstance(matchup, dict) else None


def _is_super_effective(type_matchup: dict[str, Any]) -> bool:
    if type_matchup.get("label") == "super_effective":
        return True
    multiplier = type_matchup.get("multiplier")
    return isinstance(multiplier, (int, float)) and not isinstance(multiplier, bool) and multiplier > 1
