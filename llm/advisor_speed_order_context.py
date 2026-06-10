"""Limited speed-order item context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from llm.advisor_item_legal_gate import legal_item_context_block_reason


SPEED_ORDER_CONTEXT_MODE = "limited_speed_order_item_context"
QUICK_CLAW_ITEM_ID = "quick-claw"
QUICK_CLAW_LIMITATIONS = [
    "Limited Quick Claw speed-order context only.",
    "Final move order, activation probability, priority, speed ties, Trick Room, Tailwind, paralysis, boosts, abilities, weather, and turn sequencing are not modeled.",
]


def build_speed_order_context(
    battle_input: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    attacker_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": SPEED_ORDER_CONTEXT_MODE,
        "scope": scope,
        "attacker_side": attacker_key,
        "is_final_battle_truth": False,
    }

    if not isinstance(move, dict):
        return _unavailable(base, "move_missing")

    item_profile = _item_profile(battle_input, attacker_key)
    item_status = item_profile.get("status")
    item_id = _normalized_item_id(item_profile.get("item_id"))
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_speed_order_item")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != QUICK_CLAW_ITEM_ID:
        return _unavailable(base, "unsupported_speed_order_item")

    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    return {
        **base,
        "available": True,
        "item": {
            "item_id": QUICK_CLAW_ITEM_ID,
            "status": "user_confirmed",
            "legal_status": "legal_modeled",
        },
        "speed_order_effect": {
            "type": "quick_claw",
            "effect_label": "may_affect_move_order",
            "formula_label": "quick_claw_limited_speed_order_context",
            "activation_probability_calculated": False,
            "final_move_order_calculated": False,
            "speed_tie_resolved": False,
            "priority_integrated": False,
            "turn_engine_integrated": False,
        },
        "limitations": list(QUICK_CLAW_LIMITATIONS),
    }


def _unavailable(base: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **base,
        "available": False,
        "reason": reason,
    }


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
