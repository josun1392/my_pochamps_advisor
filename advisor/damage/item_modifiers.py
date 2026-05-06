from __future__ import annotations

from advisor.damage.items import ItemEffect
from advisor.damage.q12 import Q12_ONE, M_DOUBLE, M_HALF, M_STAB


M_TYPE_BOOST = 4915
M_SMALL_BOOST = 4505
M_LIFE_ORB = 5324


def attack_stat_item_mod(
    item: ItemEffect | None,
    is_physical: bool,
    species: str,
    is_transformed: bool = False,
) -> int:
    if item is None:
        return Q12_ONE
    if item.item_id == "choice-band" and is_physical:
        return M_STAB
    if item.item_id == "choice-specs" and not is_physical:
        return M_STAB
    if item.item_id == "light-ball" and species == "pikachu":
        return M_DOUBLE
    if item.item_id == "thick-club" and is_physical:
        if species in ("cubone", "marowak", "marowak-alola"):
            return M_DOUBLE
    if item.item_id == "deep-sea-tooth" and species == "clamperl" and not is_physical:
        return M_DOUBLE
    return Q12_ONE


def defense_stat_item_mod(
    item: ItemEffect | None,
    is_physical: bool,
    species: str,
    is_nfe: bool,
    is_transformed: bool = False,
) -> int:
    if item is None:
        return Q12_ONE
    if item.item_id == "eviolite" and is_nfe:
        return M_STAB
    if item.item_id == "assault-vest" and not is_physical:
        return M_STAB
    if item.item_id == "metal-powder" and species == "ditto" and not is_transformed:
        if is_physical:
            return M_DOUBLE
    if item.item_id == "deep-sea-scale" and species == "clamperl" and not is_physical:
        return M_DOUBLE
    return Q12_ONE


def speed_stat_item_mod(
    item: ItemEffect | None,
    species: str,
    is_transformed: bool = False,
) -> int:
    if item is None:
        return Q12_ONE
    if item.item_id == "choice-scarf":
        return M_STAB
    if item.item_id == "quick-powder" and species == "ditto" and not is_transformed:
        return M_DOUBLE
    return Q12_ONE


def attacker_base_power_item_mod(
    item: ItemEffect | None,
    move_type: str,
    attacker_species: str,
    is_physical: bool,
) -> int:
    if item is None:
        return Q12_ONE
    if item.kind in ("type_boost", "type_plate"):
        if move_type in item.boosted_types:
            return item.multiplier_q12
    if item.kind == "species_orb":
        if attacker_species in item.species_lock and move_type in item.boosted_types:
            return item.multiplier_q12
    if item.item_id == "muscle-band" and is_physical:
        return M_SMALL_BOOST
    if item.item_id == "wise-glasses" and not is_physical:
        return M_SMALL_BOOST
    return Q12_ONE


def attacker_damage_item_mod(
    item: ItemEffect | None,
    is_super_effective: bool,
) -> int:
    if item is None:
        return Q12_ONE
    if item.item_id == "life-orb":
        return M_LIFE_ORB
    if item.item_id == "expert-belt" and is_super_effective:
        return M_TYPE_BOOST
    return Q12_ONE


def defender_berry_mod(
    item: ItemEffect | None,
    move_type: str,
    is_super_effective: bool,
) -> int:
    if item is None or item.kind != "type_resist_berry":
        return Q12_ONE
    if move_type not in item.boosted_types:
        return Q12_ONE
    if item.always_resist or is_super_effective:
        return M_HALF
    return Q12_ONE
