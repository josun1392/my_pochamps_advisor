from __future__ import annotations

from advisor.damage.items import ItemEffect
from advisor.damage.q12 import M_DOUBLE, M_HALF, M_STAB, Q12_ONE


M_LIFE_ORB = 5325
M_CHOICE = 6144
M_TYPE_PLATE = 4915
M_EXPERT_BELT = 4915
M_SMALL_BOOST = 4505

_TYPE_PLATE_MAP: dict[str, str] = {
    "flame-plate": "fire",
    # TODO PR #9b: expand type plate damage support.
}


def get_atk_item_modifier(
    item_id: str,
    move_category: str,
    *,
    move_type: str = "",
) -> int:
    """Returns Q12 multiplier for atk_mods. Default 4096."""
    item_id = item_id.lower()
    move_category = move_category.lower()
    move_type = move_type.lower()
    if item_id == "choice-band" and move_category == "physical":
        return M_CHOICE
    plate_type = _TYPE_PLATE_MAP.get(item_id)
    if plate_type is not None and move_type == plate_type:
        return M_TYPE_PLATE
    return Q12_ONE


def get_spa_item_modifier(
    item_id: str,
    *,
    move_type: str = "",
) -> int:
    """Returns Q12 multiplier for spa_mods. Default 4096."""
    item_id = item_id.lower()
    move_type = move_type.lower()
    if item_id == "choice-specs":
        return M_CHOICE
    plate_type = _TYPE_PLATE_MAP.get(item_id)
    if plate_type is not None and move_type == plate_type:
        return M_TYPE_PLATE
    return Q12_ONE


def get_bp_item_modifier(
    item_id: str,
    *,
    move_category: str,
) -> int:
    """Returns Q12 multiplier for bp_mods Pass 1. Default 4096."""
    item_id = item_id.lower()
    move_category = move_category.lower()
    if item_id == "muscle-band" and move_category == "physical":
        return M_SMALL_BOOST
    if item_id == "wise-glasses" and move_category == "special":
        return M_SMALL_BOOST
    return Q12_ONE


def get_final_atk_item_modifier(
    item_id: str,
    *,
    type_effectiveness_q12: int,
) -> int:
    """Returns Q12 multiplier for final_mods (attacker side). Default 4096.
    Life Orb (always-on) and Expert Belt (super-effective only) live here.
    """
    item_id = item_id.lower()
    if item_id == "life-orb":
        # TODO PR #9a: Life Orb 1/10 HP recoil
        return M_LIFE_ORB
    if item_id == "expert-belt" and type_effectiveness_q12 > Q12_ONE:
        return M_EXPERT_BELT
    return Q12_ONE


def _item_id(item: ItemEffect | None) -> str:
    return item.item_id if item is not None else ""


def attack_stat_item_mod(
    item: ItemEffect | None,
    is_physical: bool,
    species: str,
    is_transformed: bool = False,
) -> int:
    item_id = _item_id(item)
    if is_physical:
        modifier = get_atk_item_modifier(item_id, "physical")
    else:
        modifier = get_spa_item_modifier(item_id)
    if modifier != Q12_ONE:
        return modifier
    if item is None:
        return Q12_ONE
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
    return get_bp_item_modifier(
        item.item_id,
        move_category="physical" if is_physical else "special",
    )


def attacker_damage_item_mod(
    item: ItemEffect | None,
    is_super_effective: bool,
) -> int:
    return get_final_atk_item_modifier(
        _item_id(item),
        type_effectiveness_q12=Q12_ONE + 1 if is_super_effective else Q12_ONE,
    )


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
