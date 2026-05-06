from __future__ import annotations

from advisor.damage.item_modifiers import (
    attack_stat_item_mod,
    attacker_base_power_item_mod,
    attacker_damage_item_mod,
    defense_stat_item_mod,
)
from advisor.damage.items import get_item
from advisor.damage.q12 import Q12_ONE


def test_charcoal_boosts_fire_only() -> None:
    item = get_item("charcoal")
    assert attacker_base_power_item_mod(item, "fire", "charizard", False) == 4915
    assert attacker_base_power_item_mod(item, "water", "charizard", False) == Q12_ONE


def test_life_orb_boosts_any_attack() -> None:
    item = get_item("life-orb")
    assert attacker_damage_item_mod(item, False) == 5324


def test_expert_belt_requires_super_effective() -> None:
    item = get_item("expert-belt")
    assert attacker_damage_item_mod(item, True) == 4915
    assert attacker_damage_item_mod(item, False) == Q12_ONE


def test_choice_band_physical_only() -> None:
    item = get_item("choice-band")
    assert attack_stat_item_mod(item, True, "garchomp") == 6144
    assert attack_stat_item_mod(item, False, "garchomp") == Q12_ONE


def test_choice_specs_special_only() -> None:
    item = get_item("choice-specs")
    assert attack_stat_item_mod(item, False, "charizard") == 6144
    assert attack_stat_item_mod(item, True, "charizard") == Q12_ONE


def test_eviolite_requires_nfe() -> None:
    item = get_item("eviolite")
    assert defense_stat_item_mod(item, True, "pikachu", True) == 6144
    assert defense_stat_item_mod(item, False, "pikachu", True) == 6144
    assert defense_stat_item_mod(item, True, "raichu", False) == Q12_ONE


def test_light_ball_pikachu_only() -> None:
    item = get_item("light-ball")
    assert attack_stat_item_mod(item, True, "pikachu") == 8192
    assert attack_stat_item_mod(item, False, "pikachu") == 8192
    assert attack_stat_item_mod(item, False, "raichu") == Q12_ONE


def test_species_orb_requires_species_and_type() -> None:
    item = get_item("adamant-orb")
    assert attacker_base_power_item_mod(item, "steel", "dialga", True) == 4915
    assert attacker_base_power_item_mod(item, "fire", "dialga", False) == Q12_ONE
    assert attacker_base_power_item_mod(item, "steel", "garchomp", True) == Q12_ONE


def test_muscle_band_and_wise_glasses() -> None:
    assert attacker_base_power_item_mod(get_item("muscle-band"), "ground", "garchomp", True) == 4505
    assert attacker_base_power_item_mod(get_item("muscle-band"), "fire", "charizard", False) == Q12_ONE
    assert attacker_base_power_item_mod(get_item("wise-glasses"), "fire", "charizard", False) == 4505
    assert attacker_base_power_item_mod(get_item("wise-glasses"), "ground", "garchomp", True) == Q12_ONE
