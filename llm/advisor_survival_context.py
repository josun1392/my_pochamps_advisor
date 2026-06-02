"""Limited survival context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from llm.advisor_item_legal_gate import legal_item_context_block_reason


SURVIVAL_CONTEXT_MODE = "limited_item_survival_context"
FOCUS_SASH_LIMITATIONS = [
    "Limited context only.",
    "Multi-hit moves, hazards, residual damage, weather/status chip, and exact turn sequencing are not modeled.",
]


def build_focus_sash_survival_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    defender_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": SURVIVAL_CONTEXT_MODE,
        "defender_side": defender_key,
        "is_final_battle_truth": False,
        "raw_damage_rolls_changed": False,
        "limitations": list(FOCUS_SASH_LIMITATIONS),
    }

    if _is_multi_hit_move(move):
        return _unavailable(base, "multi_hit_not_supported")
    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")

    item_profile = _item_profile(battle_input, defender_key)
    item_status = item_profile.get("status")
    item_id = item_profile.get("item_id")
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_focus_sash")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != "focus-sash":
        return _unavailable(base, "no_focus_sash")
    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    hp_state = _defender_hp_state(battle_input, damage_estimate, defender_key)
    if hp_state["status"] == "unknown":
        return _unavailable(base, "hp_unknown")
    if hp_state["status"] == "not_full":
        return _unavailable(base, "hp_not_full")
    current_hp = hp_state.get("current_hp")
    if not isinstance(current_hp, int) or current_hp <= 0:
        return _unavailable(base, "defender_max_hp_missing")

    damage_range = damage_estimate.get("damage_range")
    if not isinstance(damage_range, dict):
        return _unavailable(base, "damage_estimate_missing")
    min_damage = damage_range.get("min")
    max_damage = damage_range.get("max")
    if not isinstance(min_damage, int) or not isinstance(max_damage, int):
        return _unavailable(base, "damage_estimate_missing")

    could_be_lethal = max_damage >= current_hp
    guaranteed_lethal = min_damage >= current_hp
    if not could_be_lethal:
        return _unavailable(base, "damage_not_lethal")

    return {
        **base,
        "available": True,
        "scope": scope,
        "item": {
            "item_id": "focus-sash",
            "status": "user_confirmed",
        },
        "current_hp_is_full": True,
        "incoming_damage": {
            "min": min_damage,
            "max": max_damage,
            "could_be_lethal_without_item": could_be_lethal,
            "guaranteed_lethal_without_item": guaranteed_lethal,
        },
        "survival_effect": {
            "type": "focus_sash",
            "may_survive_at_1_hp": True,
            "raw_damage_rolls_changed": False,
        },
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


def _pokemon_payload(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    pokemon = battle_input.get("pokemon")
    if not isinstance(pokemon, dict):
        return {}
    payload = pokemon.get(role_key)
    return payload if isinstance(payload, dict) else {}


def _defender_hp_state(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    defender_key: str,
) -> dict[str, Any]:
    defender = _pokemon_payload(battle_input, defender_key)
    exact_current_hp = _positive_int(defender.get("current_hp"))
    exact_max_hp = _positive_int(defender.get("max_hp"))
    if exact_current_hp is not None and exact_max_hp is not None:
        if exact_current_hp != exact_max_hp:
            return {"status": "not_full"}
        return {"status": "full", "current_hp": exact_current_hp}

    hp_percent = defender.get("hp_percent")
    if isinstance(hp_percent, int):
        if hp_percent != 100:
            return {"status": "not_full"}
        hp_reference = _defender_hp_reference(damage_estimate)
        if hp_reference is None:
            return {"status": "unknown"}
        return {"status": "full", "current_hp": hp_reference}

    return {"status": "unknown"}


def _defender_hp_reference(damage_estimate: dict[str, Any]) -> int | None:
    derived_stats = damage_estimate.get("derived_stats")
    if not isinstance(derived_stats, dict):
        return None
    defender = derived_stats.get("defender")
    if not isinstance(defender, dict):
        return None
    return _positive_int(defender.get("default_max_hp"))


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _is_multi_hit_move(move: dict[str, Any] | None) -> bool:
    if not isinstance(move, dict):
        return False
    for key in ("is_multi_hit", "multi_hit", "multihit"):
        if move.get(key) is True:
            return True
    for key in ("hit_count", "hits", "min_hits", "max_hits"):
        value = move.get(key)
        if isinstance(value, int) and value > 1:
            return True
    return False
