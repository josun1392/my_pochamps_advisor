"""Limited critical-hit context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from llm.advisor_item_legal_gate import legal_item_context_block_reason


CRITICAL_CONTEXT_MODE = "limited_critical_context"
SCOPE_LENS_ITEM_ID = "scope-lens"
SCOPE_LENS_LIMITATIONS = [
    "Limited critical-hit context only.",
    "Final critical-hit probability, critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled.",
]


def build_critical_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    *,
    attacker_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": CRITICAL_CONTEXT_MODE,
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
        return _unavailable(base, "no_scope_lens")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != SCOPE_LENS_ITEM_ID:
        return _unavailable(base, "no_scope_lens")
    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    return {
        **base,
        "available": True,
        "item": {
            "item_id": SCOPE_LENS_ITEM_ID,
            "status": "user_confirmed",
        },
        "critical_effect": {
            "type": "scope_lens",
            "effect_label": "may_increase_critical_hit_likelihood",
            "formula_label": "scope_lens_limited_critical_modifier",
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "crit_probability_integrated": False,
            "crit_adjusted_ko_integrated": False,
        },
        "limitations": list(SCOPE_LENS_LIMITATIONS),
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
