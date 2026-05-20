"""Default-assumption damage estimates for the LLM advisor payload."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.stats import StatBlock, StatInputs, final_stats, nature_from_name
from llm.advisor_payload_contract import (
    ADVISOR_DAMAGE_ASSUMPTIONS,
    ADVISOR_DAMAGE_LIMITATIONS,
)


DEFAULT_LEVEL = 50
DEFAULT_IVS = StatBlock(hp=31, atk=31, def_=31, spa=31, spd=31, spe=31)
DEFAULT_EVS = StatBlock(hp=0, atk=0, def_=0, spa=0, spd=0, spe=0)
DEFAULT_BOOSTS = StatBlock(hp=0, atk=0, def_=0, spa=0, spd=0, spe=0)


def attach_selected_move_damage_estimate(battle_input: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``battle_input`` with v0.10 damage estimates attached."""
    result = deepcopy(battle_input)
    moves = result.setdefault("moves", {})

    available_moves = moves.get("my_available_moves")
    if isinstance(available_moves, list):
        for move in available_moves:
            if isinstance(move, dict):
                move["damage_estimate"] = build_move_damage_estimate(
                    result,
                    move,
                    scope="available_move_comparison",
                )

    estimate = build_selected_move_damage_estimate(result)
    selected_move = moves.get("my_selected_move")
    if isinstance(selected_move, dict):
        selected_move["damage_estimate"] = estimate
    else:
        moves["my_selected_move"] = {"damage_estimate": estimate}
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


def build_move_damage_estimate(
    battle_input: dict[str, Any],
    move: dict[str, Any] | None,
    *,
    scope: str,
    missing_move_status: str = "unavailable_missing_move",
    missing_move_reason: str = "No move payload is available for this move slot.",
) -> dict[str, Any]:
    """Build a default-assumption damage estimate for one user-confirmed move."""
    try:
        pokemon = battle_input.get("pokemon", {})
        attacker = pokemon.get("my_active")
        defender = pokemon.get("opponent_active")

        if not isinstance(move, dict):
            return _unavailable(
                missing_move_status,
                missing_move_reason,
                scope=scope,
            )
        if not isinstance(attacker, dict) or not isinstance(defender, dict):
            return _unavailable(
                "unavailable_missing_pokemon",
                "Selected attacker or defender Pokemon data is missing.",
                move,
                scope=scope,
            )

        category = _required_str(move, "category")
        if category is None:
            return _unavailable(
                "unavailable_unsupported_category",
                "Move category is missing.",
                move,
                scope=scope,
            )
        category = category.lower()
        if category == "status":
            return _unavailable(
                "unavailable_status_move",
                "Move is a status move.",
                move,
                scope=scope,
            )
        if category not in ("physical", "special"):
            return _unavailable(
                "unavailable_unsupported_category",
                "Move category is not supported in v0.10.",
                move,
                scope=scope,
            )

        power = move.get("power")
        if not isinstance(power, int) or power <= 0:
            return _unavailable(
                "unavailable_missing_power",
                "Move has no usable base power.",
                move,
                scope=scope,
            )

        attacker_types = _types(attacker)
        defender_types = _types(defender)
        if not attacker_types or not defender_types:
            return _unavailable(
                "unavailable_missing_type",
                "Attacker or defender type data is missing.",
                move,
                scope=scope,
            )

        attacker_stats = _default_stats(attacker)
        defender_stats = _default_stats(defender)
        if attacker_stats is None or defender_stats is None:
            return _unavailable(
                "unavailable_missing_base_stats",
                "Attacker or defender base stats are missing.",
                move,
                scope=scope,
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
            )
        if move_id is None:
            move_id = move_type

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
            field=Field(is_doubles=False),
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
        )
        rolls = calc_damage_rolls(ctx)
    except Exception:
        return _unavailable(
            "unavailable_engine_error",
            "Damage engine failed while calculating the move estimate.",
            move,
            scope=scope,
        )

    return {
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
        "rolls": list(rolls),
        "assumptions": dict(ADVISOR_DAMAGE_ASSUMPTIONS),
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
        "limitations": list(ADVISOR_DAMAGE_LIMITATIONS),
    }


def _unavailable(
    status: str,
    reason: str,
    selected_move: dict[str, Any] | None = None,
    *,
    scope: str = "selected_move_only",
) -> dict[str, Any]:
    estimate: dict[str, Any] = {
        "status": status,
        "scope": scope,
        "is_final_battle_damage": False,
        "reason": reason,
        "assumptions": dict(ADVISOR_DAMAGE_ASSUMPTIONS),
        "limitations": [
            "No damage estimate is available for this selected move.",
            "Do not infer damage, OHKO/2HKO, or KO chance.",
        ],
    }
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
