from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.ability_modifiers import (
    attacker_damage_ability_mod_immunity_phase,
    attacker_move_attack_stat_ability_mod,
    defender_attack_stat_ability_mod,
    defender_base_power_ability_mod,
    defender_damage_ability_mod,
)
from advisor.damage.q12 import M_DOUBLE, M_HALF, Q12_ONE


def test_dry_skin_fire_vulnerability_is_base_power_mod() -> None:
    assert defender_base_power_ability_mod(get_ability("dry-skin"), "fire") == 5120
    assert defender_base_power_ability_mod(get_ability("dry-skin"), "water") == Q12_ONE


def test_defensive_type_mods() -> None:
    assert defender_attack_stat_ability_mod(get_ability("heatproof"), "fire") == M_HALF
    assert defender_attack_stat_ability_mod(get_ability("thick-fat"), "ice") == M_HALF
    assert defender_attack_stat_ability_mod(get_ability("water-bubble"), "fire") == M_HALF
    assert defender_attack_stat_ability_mod(get_ability("purifying-salt"), "ghost") == M_HALF
    assert defender_attack_stat_ability_mod(get_ability("thick-fat"), "water") == Q12_ONE


def test_water_bubble_offense() -> None:
    assert attacker_move_attack_stat_ability_mod(get_ability("water-bubble"), "water") == M_DOUBLE
    assert attacker_move_attack_stat_ability_mod(get_ability("water-bubble"), "fire") == Q12_ONE


def test_fluffy_combines_contact_and_fire() -> None:
    assert defender_damage_ability_mod(get_ability("fluffy"), "normal", False, True) == M_HALF
    assert defender_damage_ability_mod(get_ability("fluffy"), "fire", False, False) == M_DOUBLE
    assert defender_damage_ability_mod(get_ability("fluffy"), "fire", False, True) == Q12_ONE


def test_super_effective_damage_mods() -> None:
    assert defender_damage_ability_mod(get_ability("solid-rock"), "water", True, False) == 3072
    assert defender_damage_ability_mod(get_ability("filter"), "water", True, False) == 3072
    assert defender_damage_ability_mod(get_ability("prism-armor"), "water", True, False) == 3072
    assert defender_damage_ability_mod(get_ability("solid-rock"), "water", False, False) == Q12_ONE


def test_tinted_lens_only_on_not_very_effective() -> None:
    assert attacker_damage_ability_mod_immunity_phase(get_ability("tinted-lens"), True) == M_DOUBLE
    assert attacker_damage_ability_mod_immunity_phase(get_ability("tinted-lens"), False) == Q12_ONE
