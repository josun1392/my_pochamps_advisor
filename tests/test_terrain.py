from __future__ import annotations

from advisor.damage.modifiers import (
    sand_spdef_boost,
    snow_def_boost,
    terrain_attack_modifier,
    terrain_defense_modifier,
    weather_modifier,
)
from advisor.damage.q12 import (
    M_SAND_SPDEF,
    M_SNOW_DEF,
    M_TERRAIN_BOOST,
    M_TERRAIN_NERF,
    M_WEATHER_BOOST,
    M_WEATHER_NERF,
    Q12_ONE,
)


def test_electric_terrain_boosts_grounded_electric_move() -> None:
    assert terrain_attack_modifier("electric", "thunderbolt", "electric", True) == M_TERRAIN_BOOST


def test_electric_terrain_no_boost_if_not_grounded() -> None:
    assert terrain_attack_modifier("electric", "thunderbolt", "electric", False) == Q12_ONE


def test_grassy_terrain_weakens_grounded_earthquake_target() -> None:
    assert terrain_defense_modifier("ground", "earthquake", "grassy", True) == M_TERRAIN_NERF


def test_grassy_terrain_does_not_weaken_flying_target() -> None:
    assert terrain_defense_modifier("ground", "earthquake", "grassy", False) == Q12_ONE


def test_misty_terrain_weakens_dragon_move() -> None:
    assert terrain_defense_modifier("dragon", "dragon-pulse", "misty", True) == M_TERRAIN_NERF


def test_sun_boosts_fire() -> None:
    assert weather_modifier("fire", "sun") == M_WEATHER_BOOST


def test_rain_weakens_fire() -> None:
    assert weather_modifier("fire", "rain") == M_WEATHER_NERF


def test_heavy_rain_blocks_fire() -> None:
    assert weather_modifier("fire", "heavy-rain") == 0


def test_sand_boosts_rock_spdef() -> None:
    assert sand_spdef_boost(("rock", "dark"), "sand") == M_SAND_SPDEF


def test_snow_boosts_ice_def() -> None:
    assert snow_def_boost(("ice",), "snow") == M_SNOW_DEF
