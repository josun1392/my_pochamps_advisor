"""Limited species-stat item context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any

from advisor.damage.items import get_item
from llm.advisor_item_legal_gate import legal_item_context_block_reason


SPECIES_STAT_ITEM_CONTEXT_MODE = "limited_species_stat_item_context"
LIGHT_BALL_ITEM_ID = "light-ball"
LIGHT_BALL_LIMITATIONS = [
    "Limited species-stat item context only.",
    "Light Ball is a Pikachu-specific offensive item context.",
    "Light Ball may boost Pikachu's offensive stats in the underlying calculation when damage_estimate.item_effects marks the supported modifier as applied.",
    "This context is not final stat truth and not a final KO guarantee.",
    "This context explains supported item metadata and does not create Light-Ball-adjusted KO/OHKO/2HKO context.",
]


def build_species_stat_item_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    attacker_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": SPECIES_STAT_ITEM_CONTEXT_MODE,
        "scope": scope,
        "attacker_side": attacker_key,
        "is_final_battle_truth": False,
    }

    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")
    if not _damaging_move_category_supported(move):
        return _unavailable(base, "move_category_missing_or_unsupported")

    item_profile = _item_profile(battle_input, attacker_key)
    item_status = item_profile.get("status")
    item_id = _normalized_item_id(item_profile.get("item_id"))
    if item_status in {"none", "system_default_none"} or item_id is None:
        return _unavailable(base, "no_species_stat_item")
    if item_status != "user_confirmed":
        return _unavailable(base, "item_not_user_confirmed")
    if item_id != LIGHT_BALL_ITEM_ID:
        return _unavailable(base, "not_species_stat_item")

    legal_block_reason = legal_item_context_block_reason(item_id)
    if legal_block_reason is not None:
        return _unavailable(base, legal_block_reason)

    item_effect = get_item(item_id)
    if item_effect is None or item_effect.kind != "species_stat":
        return _unavailable(base, "species_stat_metadata_missing")

    supported_species = tuple(species for species in item_effect.species_lock if isinstance(species, str))
    if not supported_species:
        return _unavailable(base, "supported_species_missing")

    holder_species = _holder_species_id(battle_input, attacker_key)
    if holder_species is None:
        return _unavailable(base, "holder_species_missing")
    if holder_species not in supported_species:
        return _unavailable(base, "holder_species_not_supported")

    boosted_stats = tuple(stat for stat in item_effect.boosted_stats if isinstance(stat, str))
    if not boosted_stats:
        return _unavailable(base, "boosted_stats_missing")

    item_effects = damage_estimate.get("item_effects")
    attacker_item_effects = item_effects.get("attacker_item") if isinstance(item_effects, dict) else None
    damage_item_status = (
        attacker_item_effects.get("status") if isinstance(attacker_item_effects, dict) else "unknown"
    )

    return {
        **base,
        "available": True,
        "item": {
            "item_id": LIGHT_BALL_ITEM_ID,
            "status": "user_confirmed",
            "legal_status": "legal_modeled",
        },
        "species_stat_effect": {
            "holder_species_id": holder_species,
            "supported_species": list(supported_species),
            "boosted_stats": list(boosted_stats),
            "effect_label": "may_boost_pikachu_offensive_stats",
            "formula_label": "species_stat_item_limited_modifier_context",
            "damage_estimate_item_effect_status": damage_item_status,
            "raw_damage_rolls_changed": False,
            "ko_context_changed": False,
            "species_stat_adjusted_ko_integrated": False,
            "species_stat_adjusted_ohko_2hko_integrated": False,
            "final_stats_inferred": False,
        },
        "limitations": list(LIGHT_BALL_LIMITATIONS),
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


def _damaging_move_category_supported(move: dict[str, Any] | None) -> bool:
    if not isinstance(move, dict):
        return False
    category = move.get("category")
    return isinstance(category, str) and category.lower() in {"physical", "special"}


def _item_profile(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    item_profiles = battle_input.get("item_profiles")
    if not isinstance(item_profiles, dict):
        return {}
    profile = item_profiles.get(role_key)
    return profile if isinstance(profile, dict) else {}


def _holder_species_id(battle_input: dict[str, Any], role_key: str) -> str | None:
    pokemon = battle_input.get("pokemon")
    if not isinstance(pokemon, dict):
        return None
    holder = pokemon.get(role_key)
    if not isinstance(holder, dict):
        return None
    for key in ("species_id", "name_en", "id"):
        value = holder.get(key)
        normalized = _normalized_species_id(value)
        if normalized is not None:
            return normalized
    return None


def _normalized_item_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _normalized_species_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().lower().replace("_", "-").replace(" ", "-")
