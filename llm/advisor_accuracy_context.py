"""Limited accuracy context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from llm.advisor_item_legal_gate import legal_item_context_block_reason


ACCURACY_CONTEXT_MODE = "limited_accuracy_context"
BRIGHT_POWDER_ITEM_ID = "bright-powder"
BRIGHT_POWDER_LIMITATIONS = [
    "Limited accuracy context only.",
    "Accuracy/evasion stages, ability interactions, weather, multi-hit accuracy, and turn sequencing are not modeled.",
]


def build_accuracy_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    defender_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": ACCURACY_CONTEXT_MODE,
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
        return _unavailable(base, "no_bright_powder")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != BRIGHT_POWDER_ITEM_ID:
        return _unavailable(base, "no_bright_powder")
    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    base_accuracy = _move_accuracy(move)
    if base_accuracy is None:
        return _unavailable(base, "move_accuracy_missing")

    return {
        **base,
        "available": True,
        "item": {
            "item_id": BRIGHT_POWDER_ITEM_ID,
            "status": "user_confirmed",
        },
        "move_accuracy": {
            "base_accuracy": base_accuracy,
            "accuracy_source": "move_metadata",
            "accuracy_known": True,
        },
        "accuracy_effect": {
            "type": "bright_powder",
            "effect_label": "may_reduce_hit_reliability",
            "formula_label": "bright_powder_limited_modifier",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "hit_probability_integrated": False,
        },
        "limitations": list(BRIGHT_POWDER_LIMITATIONS),
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


def _move_accuracy(move: dict[str, Any] | None) -> int | float | None:
    if not isinstance(move, dict):
        return None
    accuracy = move.get("accuracy")
    if isinstance(accuracy, bool):
        return None
    if isinstance(accuracy, int) and accuracy > 0:
        return accuracy
    if isinstance(accuracy, float) and accuracy > 0:
        return accuracy
    return None
