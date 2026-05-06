from __future__ import annotations

from advisor.damage.item_modifiers import (
    attacker_damage_item_mod,
    get_atk_item_modifier,
    get_bp_item_modifier,
    get_final_atk_item_modifier,
    get_spa_item_modifier,
)
from advisor.damage.items import get_item
from advisor.damage.q12 import Q12_ONE


def test_life_orb_boosts_final_mods() -> None:
    assert get_final_atk_item_modifier("life-orb", type_effectiveness_q12=Q12_ONE) == 5325
    assert get_final_atk_item_modifier("life-orb", type_effectiveness_q12=8192) == 5325
    assert attacker_damage_item_mod(get_item("life-orb"), False) == 5325
    assert attacker_damage_item_mod(get_item("life-orb"), True) == 5325
    assert get_atk_item_modifier("life-orb", "physical") == Q12_ONE
    assert get_spa_item_modifier("life-orb") == Q12_ONE


def test_choice_band_physical_only() -> None:
    assert get_atk_item_modifier("choice-band", "physical") == 6144
    assert get_atk_item_modifier("choice-band", "special") == Q12_ONE


def test_choice_specs_special_only() -> None:
    assert get_spa_item_modifier("choice-specs") == 6144
    assert get_atk_item_modifier("choice-specs", "physical") == Q12_ONE


def test_choice_scarf_has_no_damage_modifier() -> None:
    assert get_atk_item_modifier("choice-scarf", "physical") == Q12_ONE
    assert get_spa_item_modifier("choice-scarf") == Q12_ONE
    assert get_bp_item_modifier("choice-scarf", move_category="physical") == Q12_ONE


def test_muscle_band_physical_only() -> None:
    assert get_bp_item_modifier("muscle-band", move_category="physical") == 4505
    assert get_bp_item_modifier("muscle-band", move_category="special") == Q12_ONE


def test_wise_glasses_special_only() -> None:
    assert get_bp_item_modifier("wise-glasses", move_category="special") == 4505
    assert get_bp_item_modifier("wise-glasses", move_category="physical") == Q12_ONE


def test_expert_belt_strict_super_effective_boundary() -> None:
    assert get_final_atk_item_modifier("expert-belt", type_effectiveness_q12=4096) == Q12_ONE
    assert get_final_atk_item_modifier("expert-belt", type_effectiveness_q12=4097) == 4915


def test_flame_plate_boosts_fire_only() -> None:
    assert get_spa_item_modifier("flame-plate", move_type="fire") == 4915
    assert get_atk_item_modifier("flame-plate", "physical", move_type="fire") == 4915
    assert get_spa_item_modifier("flame-plate", move_type="water") == Q12_ONE
    assert get_atk_item_modifier("flame-plate", "physical", move_type="water") == Q12_ONE
