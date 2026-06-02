"""Default-assumption damage estimates for the LLM advisor payload."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.items import ItemEffect, get_item
from advisor.damage.modifiers.core import type_effectiveness_with_field
from advisor.damage.stats import StatBlock, StatInputs, final_stats, nature_from_name
from advisor.damage.types import load_type_chart
from llm.advisor_payload_contract import (
    ADVISOR_DAMAGE_ASSUMPTIONS,
    ADVISOR_DAMAGE_LIMITATIONS,
    ADVISOR_DEFAULT_WITH_DAMAGE_ITEM_PROFILE,
    ADVISOR_DEFAULT_ASSUMPTION_PROFILE,
    ADVISOR_OPPONENT_DAMAGE_LIMITATIONS,
    ADVISOR_USER_CONFIRMED_FINAL_STATS_WITH_DAMAGE_ITEM_PROFILE,
    ADVISOR_USER_CONFIRMED_FINAL_STATS_PROFILE,
)
from llm.advisor_accuracy_context import build_accuracy_context
from llm.advisor_critical_context import build_critical_context
from llm.advisor_flinch_context import build_flinch_context
from llm.advisor_ko_context import build_ko_context
from llm.advisor_multi_hit_context import build_multi_hit_context
from llm.advisor_recovery_context import build_recovery_context
from llm.advisor_survival_context import build_focus_sash_survival_context


DEFAULT_LEVEL = 50
DEFAULT_IVS = StatBlock(hp=31, atk=31, def_=31, spa=31, spd=31, spe=31)
DEFAULT_EVS = StatBlock(hp=0, atk=0, def_=0, spa=0, spd=0, spe=0)
DEFAULT_BOOSTS = StatBlock(hp=0, atk=0, def_=0, spa=0, spd=0, spe=0)
SUPPORTED_ATTACKER_DAMAGE_ITEMS = {
    "choice-band",
    "choice-specs",
    "life-orb",
    "muscle-band",
    "wise-glasses",
}
TYPE_BOOSTING_DAMAGE_MODIFIER = 1.2
PHYSICAL_DAMAGE_ITEMS = {"choice-band", "muscle-band"}
SPECIAL_DAMAGE_ITEMS = {"choice-specs", "wise-glasses"}
ALWAYS_DAMAGE_ITEMS = {"life-orb"}
ITEM_UNAPPLIED_EFFECTS = {
    "choice-band": ["choice_lock"],
    "choice-specs": ["choice_lock"],
    "life-orb": ["recoil"],
}
LEGAL_UNMODELED_ITEM_EFFECTS = {
    "choice-scarf": ["speed_order", "choice_lock"],
    "focus-band": ["survival"],
    "focus-sash": ["survival"],
    "leftovers": ["recovery"],
    "sitrus-berry": ["recovery"],
    "quick-claw": ["speed_order"],
    "scope-lens": ["critical_hit"],
    "kings-rock": ["flinch"],
    "loaded-dice": ["multi_hit"],
}


def attach_selected_move_damage_estimate(battle_input: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``battle_input`` with v0.10 damage estimates attached."""
    result = deepcopy(battle_input)
    moves = result.setdefault("moves", {})

    available_moves = moves.get("my_available_moves")
    if isinstance(available_moves, list):
        for move in available_moves:
            if isinstance(move, dict):
                estimate = build_move_damage_estimate(
                    result,
                    move,
                    scope="available_move_comparison",
                )
                move["damage_estimate"] = estimate
                move["ko_context"] = build_ko_context(
                    result,
                    estimate,
                    defender_key="opponent_active",
                    scope="available_move_comparison",
                )
                move["recovery_context"] = build_recovery_context(
                    result,
                    estimate,
                    defender_key="opponent_active",
                    scope="available_move_comparison",
                )
                move["accuracy_context"] = build_accuracy_context(
                    result,
                    estimate,
                    move,
                    defender_key="opponent_active",
                    scope="available_move_comparison",
                )
                move["critical_context"] = build_critical_context(
                    result,
                    estimate,
                    attacker_key="my_active",
                    scope="available_move_comparison",
                )
                move["flinch_context"] = build_flinch_context(
                    result,
                    estimate,
                    attacker_key="my_active",
                    scope="available_move_comparison",
                )
                move["multi_hit_context"] = build_multi_hit_context(
                    result,
                    estimate,
                    move,
                    attacker_key="my_active",
                    scope="available_move_comparison",
                )
                move["survival_context"] = build_focus_sash_survival_context(
                    result,
                    estimate,
                    move,
                    defender_key="opponent_active",
                    scope="available_move_comparison",
                )

    estimate = build_selected_move_damage_estimate(result)
    selected_move = moves.get("my_selected_move")
    if isinstance(selected_move, dict):
        selected_move["damage_estimate"] = estimate
        selected_move["ko_context"] = build_ko_context(
            result,
            estimate,
            defender_key="opponent_active",
            scope="selected_move_only",
        )
        selected_move["recovery_context"] = build_recovery_context(
            result,
            estimate,
            defender_key="opponent_active",
            scope="selected_move_only",
        )
        selected_move["accuracy_context"] = build_accuracy_context(
            result,
            estimate,
            selected_move,
            defender_key="opponent_active",
            scope="selected_move_only",
        )
        selected_move["critical_context"] = build_critical_context(
            result,
            estimate,
            attacker_key="my_active",
            scope="selected_move_only",
        )
        selected_move["flinch_context"] = build_flinch_context(
            result,
            estimate,
            attacker_key="my_active",
            scope="selected_move_only",
        )
        selected_move["multi_hit_context"] = build_multi_hit_context(
            result,
            estimate,
            selected_move,
            attacker_key="my_active",
            scope="selected_move_only",
        )
        selected_move["survival_context"] = build_focus_sash_survival_context(
            result,
            estimate,
            selected_move,
            defender_key="opponent_active",
            scope="selected_move_only",
        )
    else:
        moves["my_selected_move"] = {
            "damage_estimate": estimate,
            "ko_context": build_ko_context(
                result,
                estimate,
                defender_key="opponent_active",
                scope="selected_move_only",
            ),
            "recovery_context": build_recovery_context(
                result,
                estimate,
                defender_key="opponent_active",
                scope="selected_move_only",
            ),
            "accuracy_context": build_accuracy_context(
                result,
                estimate,
                None,
                defender_key="opponent_active",
                scope="selected_move_only",
            ),
            "critical_context": build_critical_context(
                result,
                estimate,
                attacker_key="my_active",
                scope="selected_move_only",
            ),
            "flinch_context": build_flinch_context(
                result,
                estimate,
                attacker_key="my_active",
                scope="selected_move_only",
            ),
            "multi_hit_context": build_multi_hit_context(
                result,
                estimate,
                None,
                attacker_key="my_active",
                scope="selected_move_only",
            ),
            "survival_context": build_focus_sash_survival_context(
                result,
                estimate,
                None,
                defender_key="opponent_active",
                scope="selected_move_only",
            ),
        }
    return result


def attach_opponent_known_move_damage_estimates(battle_input: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``battle_input`` with opponent known move estimates."""
    result = deepcopy(battle_input)
    opponent_moves = result.get("opponent_moves")
    if not isinstance(opponent_moves, dict):
        return result

    known_moves = opponent_moves.get("known_moves")
    if not isinstance(known_moves, list):
        return result

    for move in known_moves:
        if isinstance(move, dict):
            estimate = build_opponent_known_move_damage_estimate(result, move)
            move["damage_estimate"] = estimate
            move["ko_context"] = build_ko_context(
                result,
                estimate,
                defender_key="my_active",
                scope="opponent_known_move_only",
            )
            move["recovery_context"] = build_recovery_context(
                result,
                estimate,
                defender_key="my_active",
                scope="opponent_known_move_only",
            )
            move["accuracy_context"] = build_accuracy_context(
                result,
                estimate,
                move,
                defender_key="my_active",
                scope="opponent_known_move_only",
            )
            move["critical_context"] = build_critical_context(
                result,
                estimate,
                attacker_key="opponent_active",
                scope="opponent_known_move_only",
            )
            move["flinch_context"] = build_flinch_context(
                result,
                estimate,
                attacker_key="opponent_active",
                scope="opponent_known_move_only",
            )
            move["multi_hit_context"] = build_multi_hit_context(
                result,
                estimate,
                move,
                attacker_key="opponent_active",
                scope="opponent_known_move_only",
            )
            move["survival_context"] = build_focus_sash_survival_context(
                result,
                estimate,
                move,
                defender_key="my_active",
                scope="opponent_known_move_only",
            )
    return result


def build_selected_move_damage_estimate(battle_input: dict[str, Any]) -> dict[str, Any]:
    """Build a selected-move damage estimate from an advisor payload."""
    moves = battle_input.get("moves", {})
    selected_move = moves.get("my_selected_move") if isinstance(moves, dict) else None
    return build_move_damage_estimate(
        battle_input,
        selected_move,
        scope="selected_move_only",
        missing_move_status="unavailable_no_selected_move",
        missing_move_reason="No selected move is assigned to the selected move slot.",
    )


def build_opponent_known_move_damage_estimate(
    battle_input: dict[str, Any],
    move: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a damage estimate for one user-confirmed opponent move."""
    return build_move_damage_estimate(
        battle_input,
        move,
        scope="opponent_known_move_only",
        attacker_key="opponent_active",
        defender_key="my_active",
        target="my_active",
        limitations=ADVISOR_OPPONENT_DAMAGE_LIMITATIONS,
        missing_move_status="unavailable_no_known_move",
        missing_move_reason="No opponent known move payload is available for this move slot.",
        status_move_reason="Selected opponent known move is a status move or has no power.",
    )


def build_move_damage_estimate(
    battle_input: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    scope: str,
    attacker_key: str = "my_active",
    defender_key: str = "opponent_active",
    target: str | None = None,
    limitations: list[str] | tuple[str, ...] | None = None,
    missing_move_status: str = "unavailable_missing_move",
    missing_move_reason: str = "No move payload is available for this move slot.",
    status_move_reason: str = "Move is a status move.",
) -> dict[str, Any]:
    """Build a default-assumption damage estimate for one user-confirmed move."""
    estimate_limitations = list(limitations if limitations is not None else ADVISOR_DAMAGE_LIMITATIONS)
    try:
        pokemon = battle_input.get("pokemon", {})
        attacker = pokemon.get(attacker_key)
        defender = pokemon.get(defender_key)

        if not isinstance(move, dict):
            return _unavailable(
                missing_move_status,
                missing_move_reason,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )
        if not isinstance(attacker, dict) or not isinstance(defender, dict):
            return _unavailable(
                "unavailable_missing_pokemon",
                "Selected attacker or defender Pokemon data is missing.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )

        category = _required_str(move, "category")
        if category is None:
            return _unavailable(
                "unavailable_unsupported_category",
                "Move category is missing.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )
        category = category.lower()
        if category == "status":
            return _unavailable(
                "unavailable_status_move",
                status_move_reason,
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )
        if category not in ("physical", "special"):
            return _unavailable(
                "unavailable_unsupported_category",
                "Move category is not supported in v0.14.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )

        power = move.get("power")
        if not isinstance(power, int) or power <= 0:
            return _unavailable(
                "unavailable_missing_power",
                "Move has no usable base power.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )

        attacker_types = _types(attacker)
        defender_types = _types(defender)
        if not attacker_types or not defender_types:
            return _unavailable(
                "unavailable_missing_type",
                "Attacker or defender type data is missing.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )

        attacker_stats = _stats_for_role(battle_input, attacker, attacker_key)
        defender_stats = _stats_for_role(battle_input, defender, defender_key)
        if attacker_stats is None or defender_stats is None:
            return _unavailable(
                "unavailable_missing_base_stats",
                "Attacker or defender base stats are missing.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )

        is_physical = category == "physical"
        attack_stat = attacker_stats.atk if is_physical else attacker_stats.spa
        defense_stat = defender_stats.def_ if is_physical else defender_stats.spd
        attack_stat_name = "atk" if is_physical else "spa"
        defense_stat_name = "def" if is_physical else "spd"

        move_type = _required_str(move, "type")
        move_id = _required_str(move, "move_id")
        if move_type is None:
            return _unavailable(
                "unavailable_missing_type",
                "Move type is missing.",
                move,
                scope=scope,
                target=target,
                limitations=estimate_limitations,
            )
        if move_id is None:
            move_id = move_type
        attacker_item_effect = _attacker_item_for_damage(
            battle_input,
            attacker_key=attacker_key,
            move_category=category,
            move_type=move_type,
        )

        field = Field(is_doubles=False)
        type_effectiveness = type_effectiveness_with_field(
            move_type,
            defender_types,
            load_type_chart(),
            field,
        )

        ctx = DamageContext(
            attacker_level=DEFAULT_LEVEL,
            move_power=power,
            attack_stat=attack_stat,
            defense_stat=defense_stat,
            move_type=move_type,
            move_id=move_id,
            attacker_types=attacker_types,
            defender_types=defender_types,
            is_physical=is_physical,
            is_critical=False,
            is_spread=False,
            field=field,
            attacker_species=str(attacker.get("name_en", "")),
            defender_species=str(defender.get("name_en", "")),
            attacker_stats=attacker_stats,
            defender_stats=defender_stats,
            attacker_boosts=DEFAULT_BOOSTS,
            defender_boosts=DEFAULT_BOOSTS,
            attacker_hp_current=attacker_stats.hp,
            attacker_hp_max=attacker_stats.hp,
            defender_hp_current=None,
            defender_hp_max=defender_stats.hp,
            attacker_item=attacker_item_effect,
        )
        rolls = calc_damage_rolls(ctx)
    except Exception:
        return _unavailable(
            "unavailable_engine_error",
            "Damage engine failed while calculating the move estimate.",
            move,
            scope=scope,
            target=target,
            limitations=estimate_limitations,
        )

    item_effects = _item_effects_summary(
        battle_input,
        attacker_key=attacker_key,
        defender_key=defender_key,
        move_category=category,
        move_type=move_type,
        applied_attacker_item=attacker_item_effect,
    )

    estimate = {
        "status": "available_with_default_assumptions",
        "scope": scope,
        "is_final_battle_damage": False,
        "selected_move_id": move_id,
        "damage_range": {
            "min": min(rolls),
            "max": max(rolls),
        },
        "percent_range": {
            "min": _percent(min(rolls), defender_stats.hp),
            "max": _percent(max(rolls), defender_stats.hp),
            "denominator": "default_defender_max_hp",
        },
        "type_effectiveness": {
            "multiplier": type_effectiveness,
            "label": _type_effectiveness_label(type_effectiveness),
        },
        "rolls": list(rolls),
        "assumption_profile": _assumption_profile_for_roles(
            battle_input,
            attacker_key=attacker_key,
            defender_key=defender_key,
            damage_item_applied=item_effects["attacker_item"]["status"] == "applied",
        ),
        "item_effects": item_effects,
        "assumptions": _assumptions_for_item_effects(item_effects),
        "derived_stats": {
            "attacker": {
                "attack_stat_used": attack_stat,
                "attack_stat_name": attack_stat_name,
            },
            "defender": {
                "defense_stat_used": defense_stat,
                "defense_stat_name": defense_stat_name,
                "default_max_hp": defender_stats.hp,
            },
        },
        "limitations": estimate_limitations,
    }
    if target is not None:
        estimate["target"] = target
    return estimate


def default_item_profiles_payload() -> dict[str, dict[str, Any]]:
    """Build the default v0.16 no-item item profile payload."""
    return {
        "my_active": _system_default_none_item_profile(),
        "opponent_active": _system_default_none_item_profile(),
    }


def _unavailable(
    status: str,
    reason: str,
    selected_move: dict[str, Any] | None = None,
    *,
    scope: str = "selected_move_only",
    target: str | None = None,
    limitations: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    estimate: dict[str, Any] = {
        "status": status,
        "scope": scope,
        "is_final_battle_damage": False,
        "reason": reason,
        "assumption_profile": dict(ADVISOR_DEFAULT_ASSUMPTION_PROFILE),
        "assumptions": dict(ADVISOR_DAMAGE_ASSUMPTIONS),
        "limitations": list(
            limitations
            if limitations is not None
            else [
                "No damage estimate is available for this selected move.",
                "Do not infer damage, OHKO/2HKO, or KO chance.",
            ]
        ),
    }
    if target is not None:
        estimate["target"] = target
    if isinstance(selected_move, dict):
        move_id = selected_move.get("move_id")
        if isinstance(move_id, str):
            estimate["selected_move_id"] = move_id
    return estimate


def _default_stats(pokemon: dict[str, Any]) -> StatBlock | None:
    base = pokemon.get("base_stats")
    if not isinstance(base, dict):
        return None
    try:
        base_block = StatBlock(
            hp=int(base["hp"]),
            atk=int(base["attack"]),
            def_=int(base["defense"]),
            spa=int(base["special-attack"]),
            spd=int(base["special-defense"]),
            spe=int(base["speed"]),
        )
    except (KeyError, TypeError, ValueError):
        return None

    nature_plus, nature_minus = nature_from_name("hardy")
    return final_stats(
        StatInputs(
            base=base_block,
            evs=DEFAULT_EVS,
            ivs=DEFAULT_IVS,
            nature_plus=nature_plus,
            nature_minus=nature_minus,
            level=DEFAULT_LEVEL,
            rule_set="gen9",
            species=str(pokemon.get("name_en", "")),
        )
    )


def _stats_for_role(
    battle_input: dict[str, Any],
    pokemon: dict[str, Any],
    role_key: str,
) -> StatBlock | None:
    final_stat_block = _final_stats_from_profile(battle_input, role_key)
    if final_stat_block is not None:
        return final_stat_block
    return _default_stats(pokemon)


def _final_stats_from_profile(battle_input: dict[str, Any], role_key: str) -> StatBlock | None:
    stat_profiles = battle_input.get("stat_profiles")
    if not isinstance(stat_profiles, dict):
        return None
    profile = stat_profiles.get(role_key)
    if not isinstance(profile, dict) or profile.get("status") != "user_confirmed_final_stats":
        return None
    final_stats = profile.get("final_stats")
    if not isinstance(final_stats, dict):
        return None
    try:
        values = {
            "hp": int(final_stats["hp"]),
            "atk": int(final_stats["atk"]),
            "def_": int(final_stats["def"]),
            "spa": int(final_stats["spa"]),
            "spd": int(final_stats["spd"]),
            "spe": int(final_stats["spe"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
    if any(value < 1 for value in values.values()):
        return None
    return StatBlock(**values)


def _assumption_profile_for_roles(
    battle_input: dict[str, Any],
    *,
    attacker_key: str,
    defender_key: str,
    damage_item_applied: bool = False,
) -> dict[str, Any]:
    attacker_status = _stat_profile_status(battle_input, attacker_key)
    defender_status = _stat_profile_status(battle_input, defender_key)
    if attacker_status == "user_confirmed_final_stats" or defender_status == "user_confirmed_final_stats":
        profile = dict(
            ADVISOR_USER_CONFIRMED_FINAL_STATS_WITH_DAMAGE_ITEM_PROFILE
            if damage_item_applied
            else ADVISOR_USER_CONFIRMED_FINAL_STATS_PROFILE
        )
        profile["stats_used"] = {
            "attacker": attacker_status,
            "defender": defender_status,
        }
        profile["damage_item_applied"] = damage_item_applied
        return profile
    if damage_item_applied:
        profile = dict(ADVISOR_DEFAULT_WITH_DAMAGE_ITEM_PROFILE)
        profile["stats_used"] = {
            "attacker": attacker_status,
            "defender": defender_status,
        }
        profile["damage_item_applied"] = True
        return profile
    return dict(ADVISOR_DEFAULT_ASSUMPTION_PROFILE)


def _stat_profile_status(battle_input: dict[str, Any], role_key: str) -> str:
    return (
        "user_confirmed_final_stats"
        if _final_stats_from_profile(battle_input, role_key) is not None
        else "default_assumption"
    )


def _types(pokemon: dict[str, Any]) -> tuple[str, ...]:
    types = pokemon.get("types")
    if not isinstance(types, list):
        return ()
    return tuple(type_name for type_name in types if isinstance(type_name, str) and type_name)


def _required_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _percent(damage: int, hp: int) -> float:
    if hp <= 0:
        return 0.0
    return round(damage / hp * 100, 1)


def _type_effectiveness_label(multiplier: float) -> str:
    if multiplier == 0.0:
        return "immune"
    if multiplier < 1.0:
        return "not_very_effective"
    if multiplier > 1.0:
        return "super_effective"
    return "neutral"


def _system_default_none_item_profile() -> dict[str, Any]:
    return {
        "status": "system_default_none",
        "source": "system_default",
        "item_id": None,
        "name_en": None,
        "name_ko": None,
        "effects_scope": [],
        "damage_modifier_status": "not_applicable",
        "notes": ["No item is assumed by default."],
    }


def _assumptions_for_item_effects(item_effects: dict[str, Any]) -> dict[str, Any]:
    assumptions = dict(ADVISOR_DAMAGE_ASSUMPTIONS)
    attacker_item = item_effects.get("attacker_item")
    if isinstance(attacker_item, dict) and attacker_item.get("status") == "applied":
        assumptions["item"] = "supported_attacker_damage_item_applied"
    return assumptions


def _item_profile(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    item_profiles = battle_input.get("item_profiles")
    if not isinstance(item_profiles, dict):
        return _system_default_none_item_profile()
    profile = item_profiles.get(role_key)
    if not isinstance(profile, dict):
        return _system_default_none_item_profile()
    return profile


def _attacker_item_for_damage(
    battle_input: dict[str, Any],
    *,
    attacker_key: str,
    move_category: str,
    move_type: str,
) -> ItemEffect | None:
    profile = _item_profile(battle_input, attacker_key)
    item_id = profile.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        return None
    item_id = item_id.lower()
    type_boost_item = _catalog_type_boost_item(profile)
    if type_boost_item is not None and move_type.lower() in type_boost_item.boosted_types:
        return type_boost_item
    if not _is_supported_attacker_item_for_category(item_id, move_category):
        return None
    return get_item(item_id)


def _is_supported_attacker_item_for_category(item_id: str, move_category: str) -> bool:
    if item_id not in SUPPORTED_ATTACKER_DAMAGE_ITEMS:
        return False
    if item_id in ALWAYS_DAMAGE_ITEMS:
        return True
    if item_id in PHYSICAL_DAMAGE_ITEMS:
        return move_category == "physical"
    if item_id in SPECIAL_DAMAGE_ITEMS:
        return move_category == "special"
    return False


def _item_effects_summary(
    battle_input: dict[str, Any],
    *,
    attacker_key: str,
    defender_key: str,
    move_category: str,
    move_type: str,
    applied_attacker_item: ItemEffect | None,
) -> dict[str, Any]:
    attacker_profile = _item_profile(battle_input, attacker_key)
    defender_profile = _item_profile(battle_input, defender_key)
    return {
        "attacker_item": _item_effect_summary(
            attacker_profile,
            role="attacker",
            move_category=move_category,
            move_type=move_type,
            applied_item=applied_attacker_item,
        ),
        "defender_item": _item_effect_summary(
            defender_profile,
            role="defender",
            move_category=move_category,
            move_type=move_type,
            applied_item=None,
        ),
    }


def _item_effect_summary(
    profile: dict[str, Any],
    *,
    role: str,
    move_category: str,
    move_type: str,
    applied_item: ItemEffect | None,
) -> dict[str, Any]:
    status = str(profile.get("status", "system_default_none"))
    item_id_value = profile.get("item_id")
    item_id = item_id_value.lower() if isinstance(item_id_value, str) and item_id_value else None
    if item_id is None:
        return {
            "item_id": None,
            "status": status,
            "applied_effects": [],
            "unapplied_effects": [],
        }

    unapplied_effects = list(ITEM_UNAPPLIED_EFFECTS.get(item_id, []))
    if role != "attacker":
        return {
            "item_id": item_id,
            "status": "not_applied",
            "applied_effects": [],
            "unapplied_effects": ["defender_item_effects_not_supported_in_v0.16", *unapplied_effects],
        }
    type_boost_summary = _type_boosting_item_effect_summary(
        profile,
        item_id=item_id,
        move_type=move_type,
        applied_item=applied_item,
    )
    if type_boost_summary is not None:
        return type_boost_summary
    if _is_legal_item_not_applied(profile):
        return {
            "item_id": item_id,
            "status": "not_applied",
            "applied_effects": [],
            "unapplied_effects": _legal_unmodeled_effects(item_id),
        }
    if applied_item is not None:
        return {
            "item_id": item_id,
            "status": "applied",
            "applied_effects": ["damage_modifier"],
            "unapplied_effects": unapplied_effects,
        }
    if item_id in SUPPORTED_ATTACKER_DAMAGE_ITEMS:
        return {
            "item_id": item_id,
            "status": "not_applicable",
            "applied_effects": [],
            "unapplied_effects": [
                f"damage_modifier_not_applicable_to_{move_category}_move",
                *unapplied_effects,
            ],
        }
    return {
        "item_id": item_id,
        "status": "unsupported_item",
        "applied_effects": [],
        "unapplied_effects": ["item_damage_modifier_not_supported_in_v0.16", *unapplied_effects],
    }


def _is_legal_item_not_applied(profile: dict[str, Any]) -> bool:
    return profile.get("effect_support_status") == "legal_but_not_modeled"


def _legal_unmodeled_effects(item_id: str) -> list[str]:
    return LEGAL_UNMODELED_ITEM_EFFECTS.get(item_id, ["item_effect_not_modeled_in_v0.23"])


def _catalog_type_boost_item(profile: dict[str, Any]) -> ItemEffect | None:
    if not _is_user_confirmed_legal_type_boosting_profile(profile):
        return None
    item_id_value = profile.get("item_id")
    item_id = item_id_value.lower() if isinstance(item_id_value, str) else ""
    item = get_item(item_id)
    if item is None or item.kind != "type_boost":
        return None
    return item


def _is_user_confirmed_legal_type_boosting_profile(profile: dict[str, Any]) -> bool:
    if profile.get("status") != "user_confirmed":
        return False
    legal = profile.get("legal") is True or profile.get("legality_status") == "legal"
    if not legal:
        return False
    item_id_value = profile.get("item_id")
    item_id = item_id_value.lower() if isinstance(item_id_value, str) and item_id_value else ""
    support_status = profile.get("effect_support_status")
    if support_status == "legal_and_damage_supported":
        item = get_item(item_id)
        return item is not None and item.kind == "type_boost"
    if support_status == "legal_but_not_modeled":
        return profile.get("category") == "type_boosting_item" or item_id == "fairy-feather"
    return False


def _type_boosting_item_effect_summary(
    profile: dict[str, Any],
    *,
    item_id: str,
    move_type: str,
    applied_item: ItemEffect | None,
) -> dict[str, Any] | None:
    if not _is_user_confirmed_legal_type_boosting_profile(profile):
        return None

    name_en = profile.get("name_en") if isinstance(profile.get("name_en"), str) else item_id
    catalog_item = get_item(item_id)
    if catalog_item is None or catalog_item.kind != "type_boost":
        return {
            "item_id": item_id,
            "name_en": name_en,
            "status": "unsupported_item",
            "effect_type": "type_boosting_damage_modifier",
            "applied_effects": [],
            "unapplied_effects": ["unsupported_catalog_missing"],
            "reason": "No catalog-backed damage modifier is available yet.",
        }

    boosted_type = catalog_item.boosted_types[0] if catalog_item.boosted_types else None
    base = {
        "item_id": item_id,
        "name_en": name_en,
        "effect_type": "type_boosting_damage_modifier",
        "boosted_type": boosted_type,
        "modifier": TYPE_BOOSTING_DAMAGE_MODIFIER,
    }
    if applied_item is not None and move_type.lower() in catalog_item.boosted_types:
        return {
            **base,
            "status": "applied",
            "applied_effects": ["damage_modifier"],
            "unapplied_effects": [],
            "reason": "Move type matches item boosted type.",
        }
    return {
        **base,
        "status": "not_applicable",
        "applied_effects": [],
        "unapplied_effects": ["move_type_does_not_match_boosted_type"],
        "reason": "Move type does not match item boosted type.",
    }
