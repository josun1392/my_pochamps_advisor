from __future__ import annotations

from dataclasses import dataclass

from advisor.damage.field import Field
from advisor.damage.q12 import (
    M_NEUTRAL,
    M_SAND_SPDEF,
    M_SNOW_DEF,
    M_STAB,
    M_TERA_DOUBLE_STAB,
    M_TERRAIN_BOOST,
    M_TERRAIN_NERF,
    M_WEATHER_BOOST,
    M_WEATHER_NERF,
    Q12_ONE,
)


@dataclass(frozen=True, slots=True)
class TransformState:
    is_mega: bool = False
    mega_form: str | None = None
    is_z_move: bool = False
    z_move_id: str | None = None
    is_dynamaxed: bool = False
    dynamax_level: int = 0
    is_terastallized: bool = False
    tera_type: str | None = None


def stab_modifier(move_type: str, attacker_types: tuple[str, ...]) -> int:
    return M_STAB if move_type in attacker_types else M_NEUTRAL


def calc_stab(
    attacker_types: tuple[str, ...],
    move_type: str,
    is_terastallized: bool = False,
    tera_type: str | None = None,
) -> int:
    if not is_terastallized or tera_type is None:
        return stab_modifier(move_type, attacker_types)
    tera_type = tera_type.lower()
    tera_match = move_type == tera_type
    original_stab = move_type in attacker_types
    if tera_match and original_stab:
        return M_TERA_DOUBLE_STAB
    if tera_match or original_stab:
        return M_STAB
    return Q12_ONE


def weather_modifier(move_type: str, weather: str) -> int:
    if weather in ("sun", "harsh-sunlight"):
        if move_type == "fire":
            return M_WEATHER_BOOST
        if move_type == "water":
            return 0 if weather == "harsh-sunlight" else M_WEATHER_NERF
    if weather in ("rain", "heavy-rain"):
        if move_type == "water":
            return M_WEATHER_BOOST
        if move_type == "fire":
            return 0 if weather == "heavy-rain" else M_WEATHER_NERF
    return Q12_ONE


def sand_spdef_boost(defender_types: tuple[str, ...], weather: str) -> int:
    return M_SAND_SPDEF if weather == "sand" and "rock" in defender_types else Q12_ONE


def snow_def_boost(defender_types: tuple[str, ...], weather: str) -> int:
    return M_SNOW_DEF if weather == "snow" and "ice" in defender_types else Q12_ONE


def terrain_attack_modifier(
    move_type: str,
    move_id: str,
    terrain: str,
    attacker_grounded: bool,
) -> int:
    del move_id
    if not attacker_grounded:
        return Q12_ONE
    if terrain == "electric" and move_type == "electric":
        return M_TERRAIN_BOOST
    if terrain == "grassy" and move_type == "grass":
        return M_TERRAIN_BOOST
    if terrain == "psychic" and move_type == "psychic":
        return M_TERRAIN_BOOST
    return Q12_ONE


def terrain_defense_modifier(
    move_type: str,
    move_id: str,
    terrain: str,
    defender_grounded: bool,
) -> int:
    if not defender_grounded:
        return Q12_ONE
    if terrain == "grassy" and move_id in ("earthquake", "magnitude", "bulldoze"):
        return M_TERRAIN_NERF
    if terrain == "misty" and move_type == "dragon":
        return M_TERRAIN_NERF
    return Q12_ONE


def type_effectiveness_with_field(
    move_type: str,
    defender_types: tuple[str, ...],
    chart: dict[str, dict[str, float]],
    field: Field,
) -> float:
    multiplier = 1.0
    for defender_type in defender_types:
        effectiveness = chart[move_type][defender_type]
        if field.weather == "strong-winds" and defender_type == "flying" and effectiveness > 1.0:
            effectiveness = 1.0
        multiplier *= effectiveness
    return multiplier
