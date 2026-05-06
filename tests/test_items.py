from __future__ import annotations

from advisor.damage.item_modifiers import (
    attack_stat_item_mod,
    attacker_base_power_item_mod,
    defense_stat_item_mod,
)
from advisor.damage.items import get_item
from advisor.damage.q12 import Q12_ONE


def test_type_boost_item_lookup() -> None:
    item = get_item("charcoal")
    assert item is not None
    assert item.boosted_types == ("fire",)
    assert item.multiplier_q12 == 4915


def test_life_orb_lookup() -> None:
    item = get_item("life-orb")
    assert item is not None
    assert item.multiplier_q12 == 5325


def test_charcoal_boosts_fire_only() -> None:
    item = get_item("charcoal")
    assert attacker_base_power_item_mod(item, "fire", "charizard", False) == 4915
    assert attacker_base_power_item_mod(item, "water", "charizard", False) == Q12_ONE


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


def test_missing_item_lookup() -> None:
    assert get_item(None) is None
    assert get_item("nonexistent") is None


def test_all_type_plates_lookup() -> None:
    plates = [
        "blank-plate",
        "flame-plate",
        "splash-plate",
        "zap-plate",
        "meadow-plate",
        "icicle-plate",
        "fist-plate",
        "toxic-plate",
        "earth-plate",
        "sky-plate",
        "mind-plate",
        "insect-plate",
        "stone-plate",
        "spooky-plate",
        "draco-plate",
        "dread-plate",
        "iron-plate",
        "pixie-plate",
    ]
    assert all(get_item(item_id) is not None for item_id in plates)


def test_all_type_resist_berries_lookup() -> None:
    berries = [
        "occa-berry",
        "passho-berry",
        "wacan-berry",
        "rindo-berry",
        "yache-berry",
        "chople-berry",
        "kebia-berry",
        "shuca-berry",
        "coba-berry",
        "payapa-berry",
        "tanga-berry",
        "charti-berry",
        "kasib-berry",
        "haban-berry",
        "colbur-berry",
        "babiri-berry",
        "roseli-berry",
        "chilan-berry",
    ]
    assert all(get_item(item_id) is not None for item_id in berries)


def test_soul_dew_lookup() -> None:
    item = get_item("soul-dew")
    assert item is not None
    assert item.species_lock == ("latios", "latias")
    assert item.boosted_types == ("psychic", "dragon")
