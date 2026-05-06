from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.ability_modifiers import defense_stat_ability_mod, speed_stat_ability_mod
from advisor.damage.q12 import Q12_ONE


def test_surge_surfer_boosts_speed_on_electric_terrain() -> None:
    assert speed_stat_ability_mod(get_ability("surge-surfer"), "none", False, "electric") == 8192
    assert speed_stat_ability_mod(get_ability("surge-surfer"), "none", False, "grassy") == Q12_ONE


def test_grass_pelt_boosts_physical_defense_on_grassy_terrain() -> None:
    ability = get_ability("grass-pelt")
    assert defense_stat_ability_mod(ability, True, "none", False, "grassy") == 6144
    assert defense_stat_ability_mod(ability, False, "none", False, "grassy") == Q12_ONE
    assert defense_stat_ability_mod(ability, True, "none", False, "electric") == Q12_ONE


def test_terrain_summoners_are_identified_only() -> None:
    ability = get_ability("electric-surge")
    assert ability is not None
    assert ability.category == "terrain_summon"
    assert ability.raw_data["summons"] == "electric"
    assert speed_stat_ability_mod(ability, "none", False, "electric") == Q12_ONE
