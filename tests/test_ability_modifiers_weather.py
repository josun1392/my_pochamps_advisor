from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.ability_modifiers import (
    attack_stat_ability_mod,
    attacker_base_power_ability_mod,
    speed_stat_ability_mod,
)
from advisor.damage.q12 import Q12_ONE


def test_sand_force_boosts_rock_ground_steel_in_sand() -> None:
    ability = get_ability("sand-force")
    assert attacker_base_power_ability_mod(ability, "rock", "sand", False) == 5325
    assert attacker_base_power_ability_mod(ability, "ground", "sand", False) == 5325
    assert attacker_base_power_ability_mod(ability, "steel", "sand", False) == 5325


def test_sand_force_requires_sand_and_matching_type() -> None:
    ability = get_ability("sand-force")
    assert attacker_base_power_ability_mod(ability, "normal", "sand", False) == Q12_ONE
    assert attacker_base_power_ability_mod(ability, "ground", "none", False) == Q12_ONE
    assert attacker_base_power_ability_mod(ability, "ground", "sand", True) == Q12_ONE


def test_solar_power_boosts_special_attack_in_sun() -> None:
    ability = get_ability("solar-power")
    assert attack_stat_ability_mod(ability, False, "sun", False, "none") == 6144
    assert attack_stat_ability_mod(ability, True, "sun", False, "none") == Q12_ONE
    assert attack_stat_ability_mod(ability, False, "sun", True, "none") == Q12_ONE


def test_speed_weather_abilities() -> None:
    assert speed_stat_ability_mod(get_ability("chlorophyll"), "sun", False, "none") == 8192
    assert speed_stat_ability_mod(get_ability("swift-swim"), "rain", False, "none") == 8192
    assert speed_stat_ability_mod(get_ability("sand-rush"), "sand", False, "none") == 8192
    assert speed_stat_ability_mod(get_ability("slush-rush"), "snow", False, "none") == 8192
    assert speed_stat_ability_mod(get_ability("chlorophyll"), "sun", True, "none") == Q12_ONE
