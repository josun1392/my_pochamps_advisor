"""Limited multi-hit context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from advisor.damage.multihit import move_data_for


MULTI_HIT_CONTEXT_MODE = "limited_multi_hit_context"
LOADED_DICE_ITEM_ID = "loaded-dice"
LOADED_DICE_LIMITATIONS = [
    "Limited multi-hit context only.",
    "Final hit count distribution, per-hit damage, Focus Sash interaction, King's Rock interaction, accuracy/crit per-hit handling, and turn sequencing are not modeled.",
]


def build_multi_hit_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    attacker_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": MULTI_HIT_CONTEXT_MODE,
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
        return _unavailable(base, "no_loaded_dice")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != LOADED_DICE_ITEM_ID:
        return _unavailable(base, "no_loaded_dice")

    metadata = _multi_hit_metadata(move)
    if metadata["reason"] is not None:
        return _unavailable(base, metadata["reason"])

    return {
        **base,
        "available": True,
        "item": {
            "item_id": LOADED_DICE_ITEM_ID,
            "status": "user_confirmed",
        },
        "move_metadata": {
            "is_multi_hit": True,
            "metadata_source": metadata["metadata_source"],
            "multi_hit_known": True,
        },
        "multi_hit_effect": {
            "type": "loaded_dice",
            "effect_label": "may_improve_multi_hit_reliability",
            "formula_label": "loaded_dice_limited_multihit_modifier",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "hit_count_probability_integrated": False,
            "multi_hit_adjusted_ko_integrated": False,
        },
        "limitations": list(LOADED_DICE_LIMITATIONS),
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


def _multi_hit_metadata(move: dict[str, Any] | None) -> dict[str, str | None]:
    if not isinstance(move, dict):
        return {"metadata_source": None, "reason": "move_multihit_metadata_missing"}

    explicit = _explicit_multi_hit_value(move)
    if explicit is True:
        return {"metadata_source": "move_metadata", "reason": None}
    if explicit is False:
        return {"metadata_source": "move_metadata", "reason": "move_not_multi_hit"}

    move_id = _normalized_item_id(move.get("move_id") or move.get("id") or move.get("name"))
    if move_id is None:
        return {"metadata_source": None, "reason": "move_multihit_metadata_missing"}

    move_data = move_data_for(move)
    if move_data.multihit is None:
        return {"metadata_source": "move_metadata", "reason": "move_not_multi_hit"}
    return {"metadata_source": "move_metadata", "reason": None}


def _explicit_multi_hit_value(move: dict[str, Any]) -> bool | None:
    for key in ("is_multi_hit", "multi_hit"):
        value = move.get(key)
        if isinstance(value, bool):
            return value
    multihit = move.get("multihit")
    if multihit is None:
        return None
    if isinstance(multihit, bool):
        return multihit
    if isinstance(multihit, int):
        return multihit > 1
    if isinstance(multihit, (list, tuple)):
        return len(multihit) == 2 and any(isinstance(hit, int) and hit > 1 for hit in multihit)
    return None


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
