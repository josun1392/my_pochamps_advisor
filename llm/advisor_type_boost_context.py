"""Limited type-boosting item context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from advisor.damage.items import get_item
from llm.advisor_item_legal_gate import legal_item_context_block_reason


TYPE_BOOST_CONTEXT_MODE = "limited_type_boost_context"
TYPE_BOOST_LIMITATIONS = [
    "Limited type-boost context only.",
    "This context describes a supported item modifier already represented by damage_estimate.item_effects when applicable.",
    "It does not create a separate type-boost-adjusted KO/OHKO/2HKO context.",
]


def build_type_boost_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    attacker_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": TYPE_BOOST_CONTEXT_MODE,
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
        return _unavailable(base, "no_type_boost_item")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")

    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    if item_profile.get("category") != "type_boosting_item":
        return _unavailable(base, "not_type_boosting_item")
    if item_profile.get("effect_support_status") != "legal_and_damage_supported":
        return _unavailable(base, "type_boost_metadata_missing")

    item_effect = get_item(item_id)
    if item_effect is None or item_effect.kind != "type_boost":
        return _unavailable(base, "type_boost_metadata_missing")

    boosted_type = _boosted_type(item_effect)
    if boosted_type is None:
        return _unavailable(base, "boosted_type_missing")

    move_type = _move_type(move)
    if move_type is None:
        return _unavailable(base, "move_type_missing")
    if move_type != boosted_type:
        return _unavailable(base, "move_type_does_not_match_boosted_type")

    item_effects = damage_estimate.get("item_effects")
    attacker_item_effects = item_effects.get("attacker_item") if isinstance(item_effects, dict) else None
    damage_item_status = (
        attacker_item_effects.get("status") if isinstance(attacker_item_effects, dict) else "unknown"
    )

    return {
        **base,
        "available": True,
        "item": {
            "item_id": item_id,
            "status": "user_confirmed",
            "legal_status": "legal_modeled",
        },
        "type_boost_effect": {
            "boosted_type": boosted_type,
            "move_type": move_type,
            "effect_label": "may_boost_matching_type_move",
            "formula_label": "type_boost_limited_damage_modifier_context",
            "damage_estimate_item_effect_status": damage_item_status,
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "type_boost_adjusted_ko_integrated": False,
            "type_boost_adjusted_ohko_2hko_integrated": False,
        },
        "limitations": list(TYPE_BOOST_LIMITATIONS),
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


def _boosted_type(item_effect: Any) -> str | None:
    if not item_effect.boosted_types:
        return None
    boosted_type = item_effect.boosted_types[0]
    return boosted_type if isinstance(boosted_type, str) and boosted_type else None


def _move_type(move: dict[str, Any] | None) -> str | None:
    if not isinstance(move, dict):
        return None
    move_type = move.get("type") or move.get("type_en")
    if not isinstance(move_type, str) or not move_type.strip():
        return None
    return move_type.strip().lower()
