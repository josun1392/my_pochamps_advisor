from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.ability_modifiers import (
    attack_stat_ability_mod,
    defense_stat_ability_mod,
    speed_stat_ability_mod,
)
from advisor.damage.q12 import Q12_ONE
from advisor.damage.stats import StatBlock


def test_protosynthesis_boosts_highest_attack_in_sun() -> None:
    stats = StatBlock(hp=100, atk=131, def_=100, spa=80, spd=70, spe=90)
    ability = get_ability("protosynthesis")

    assert attack_stat_ability_mod(ability, True, "sun", False, "none", stats=stats) == 5324
    assert attack_stat_ability_mod(ability, True, "sun", True, "none", stats=stats) == Q12_ONE


def test_quark_drive_boosts_highest_spa_on_electric_terrain() -> None:
    stats = StatBlock(hp=100, atk=80, def_=90, spa=140, spd=110, spe=100)
    ability = get_ability("quark-drive")

    assert attack_stat_ability_mod(ability, False, "none", False, "electric", stats=stats) == 5324
    assert attack_stat_ability_mod(ability, False, "none", False, "grassy", stats=stats) == Q12_ONE


def test_paradox_speed_uses_6144() -> None:
    stats = StatBlock(hp=100, atk=80, def_=90, spa=100, spd=110, spe=136)

    assert speed_stat_ability_mod(get_ability("quark-drive"), "none", False, "electric", stats=stats) == 6144


def test_booster_energy_activates_despite_weather_suppression() -> None:
    stats = StatBlock(hp=100, atk=80, def_=90, spa=140, spd=110, spe=100)
    ability = get_ability("protosynthesis")

    assert attack_stat_ability_mod(
        ability,
        False,
        "sun",
        True,
        "none",
        stats=stats,
        booster_active=True,
    ) == 5324


def test_locked_paradox_stat_overrides_auto_detection() -> None:
    stats = StatBlock(hp=100, atk=80, def_=90, spa=140, spd=110, spe=100)
    ability = get_ability("quark-drive")

    assert defense_stat_ability_mod(
        ability,
        True,
        "none",
        False,
        "electric",
        stats=stats,
        locked_paradox_stat="def",
    ) == 5324
