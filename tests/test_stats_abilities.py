from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.q12 import apply_damage_modifier
from advisor.damage.stats import StatBlock, StatInputs, final_stats


def _inputs(*, locked_paradox_stat: str | None = None) -> StatInputs:
    return StatInputs(
        base=StatBlock(hp=80, atk=100, def_=70, spa=120, spd=80, spe=90),
        evs=StatBlock(hp=0, atk=0, def_=0, spa=0, spd=0, spe=0),
        ivs=StatBlock(hp=31, atk=31, def_=31, spa=31, spd=31, spe=31),
        nature_plus=None,
        nature_minus=None,
        level=50,
        rule_set="gen9",
        locked_paradox_stat=locked_paradox_stat,  # type: ignore[arg-type]
    )


def test_chlorophyll_doubles_speed_in_sun() -> None:
    base = final_stats(_inputs())
    boosted = final_stats(_inputs(), ability=get_ability("chlorophyll"), weather="sun")

    assert boosted.spe == base.spe * 2


def test_solar_power_boosts_special_attack_in_sun() -> None:
    base = final_stats(_inputs())
    boosted = final_stats(_inputs(), ability=get_ability("solar-power"), weather="sun")

    assert boosted.spa == base.spa * 3 // 2


def test_grass_pelt_boosts_defense_in_grassy_terrain() -> None:
    base = final_stats(_inputs())
    boosted = final_stats(_inputs(), ability=get_ability("grass-pelt"), terrain="grassy")

    assert boosted.def_ == base.def_ * 3 // 2


def test_quark_drive_boosts_highest_stat() -> None:
    base = final_stats(_inputs())
    boosted = final_stats(_inputs(), ability=get_ability("quark-drive"), terrain="electric")

    assert boosted.spa == apply_damage_modifier(base.spa, 5324)


def test_locked_paradox_stat_is_used() -> None:
    base = final_stats(_inputs(locked_paradox_stat="spe"))
    boosted = final_stats(
        _inputs(locked_paradox_stat="spe"),
        ability=get_ability("protosynthesis"),
        weather="none",
        booster_active=True,
    )

    assert boosted.spe == base.spe * 3 // 2
