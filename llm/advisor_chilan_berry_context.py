"""Limited Chilan Berry context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from advisor.damage.items import ItemEffect, get_item
from llm.advisor_item_legal_gate import legal_item_context_block_reason


CHILAN_BERRY_CONTEXT_MODE = "limited_chilan_berry_context"
CHILAN_BERRY_ITEM_ID = "chilan-berry"
CHILAN_BERRY_LIMITATIONS = [
    "Normal-type limited Chilan Berry context only.",
    "Chilan Berry may reduce damage from a Normal-type damaging move.",
    "Raw damage rolls and ko_context remain based on the current calculator.",
    "This context is not integrated into final KO odds and is not final survival truth.",
    "Item consumption, multi-hit handling, abilities, weather, terrain, and turn sequencing are outside this context.",
]


def build_chilan_berry_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    defender_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": CHILAN_BERRY_CONTEXT_MODE,
        "scope": scope,
        "defender_side": defender_key,
        "is_final_battle_truth": False,
    }

    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")
    if not _damaging_move_supported(move):
        return _unavailable(base, "move_not_damaging")

    item_profile = _item_profile(battle_input, defender_key)
    item_status = item_profile.get("status")
    item_id = _normalized_item_id(item_profile.get("item_id"))
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_chilan_berry")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != CHILAN_BERRY_ITEM_ID:
        return _unavailable(base, "no_chilan_berry")

    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    item_effect = get_item(item_id)
    if not _is_chilan_metadata(item_effect):
        return _unavailable(base, "chilan_berry_metadata_missing")

    incoming_move_type = _move_type(move)
    if incoming_move_type is None:
        return _unavailable(base, "incoming_move_type_missing")
    if incoming_move_type != "normal":
        return _unavailable(base, "move_type_not_normal")

    return {
        **base,
        "available": True,
        "item": {
            "item_id": CHILAN_BERRY_ITEM_ID,
            "status": "user_confirmed",
            "legal_status": "legal_modeled",
        },
        "normal_resist_effect": {
            "berry_type": "normal",
            "incoming_move_type": incoming_move_type,
            "requires_super_effective_hit": False,
            "always_resist": True,
            "effect_label": "may_reduce_normal_type_hit",
            "formula_label": "chilan_berry_limited_normal_damage_reduction",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "chilan_adjusted_damage_integrated": False,
            "chilan_adjusted_ko_integrated": False,
            "item_consumption_tracked": False,
        },
        "limitations": list(CHILAN_BERRY_LIMITATIONS),
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


def _damaging_move_supported(move: dict[str, Any] | None) -> bool:
    if not isinstance(move, dict):
        return False
    category = move.get("category")
    if not isinstance(category, str) or category.lower() == "status":
        return False
    power = move.get("power")
    return isinstance(power, int) and not isinstance(power, bool) and power > 0


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


def _is_chilan_metadata(item_effect: ItemEffect | None) -> bool:
    if item_effect is None or item_effect.kind != "type_resist_berry":
        return False
    if not item_effect.always_resist:
        return False
    return _berry_type(item_effect) == "normal"


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
