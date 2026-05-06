from __future__ import annotations

from advisor.damage.items import get_item
from advisor.damage.stats import StatBlock, StatInputs, final_stats


def _inputs(species: str, *, is_nfe: bool = False) -> StatInputs:
    return StatInputs(
        base=StatBlock(hp=35, atk=55, def_=40, spa=50, spd=50, spe=90),
        evs=StatBlock(hp=0, atk=0, def_=0, spa=0, spd=0, spe=0),
        ivs=StatBlock(hp=31, atk=31, def_=31, spa=31, spd=31, spe=31),
        nature_plus=None,
        nature_minus=None,
        level=50,
        rule_set="gen9",
        species=species,
        is_nfe=is_nfe,
    )


def test_light_ball_doubles_pikachu_attacks() -> None:
    base = final_stats(_inputs("pikachu"))
    boosted = final_stats(_inputs("pikachu"), get_item("light-ball"))

    assert boosted.atk == base.atk * 2
    assert boosted.spa == base.spa * 2


def test_light_ball_does_not_boost_raichu() -> None:
    base = final_stats(_inputs("raichu"))
    boosted = final_stats(_inputs("raichu"), get_item("light-ball"))

    assert boosted == base


def test_choice_scarf_boosts_speed_only() -> None:
    base = final_stats(_inputs("garchomp"))
    boosted = final_stats(_inputs("garchomp"), get_item("choice-scarf"))

    assert boosted.spe == base.spe * 3 // 2
    assert boosted.atk == base.atk


def test_eviolite_boosts_nfe_defenses() -> None:
    base = final_stats(_inputs("pikachu", is_nfe=True))
    boosted = final_stats(_inputs("pikachu", is_nfe=True), get_item("eviolite"))

    assert boosted.def_ == base.def_ * 3 // 2
    assert boosted.spd == base.spd * 3 // 2


def test_eviolite_ignores_final_evolution() -> None:
    base = final_stats(_inputs("raichu", is_nfe=False))
    boosted = final_stats(_inputs("raichu", is_nfe=False), get_item("eviolite"))

    assert boosted == base


def test_deep_sea_tooth_boosts_clamperl_special_attack() -> None:
    base = final_stats(_inputs("clamperl"))
    boosted = final_stats(_inputs("clamperl"), get_item("deep-sea-tooth"))

    assert boosted.spa == base.spa * 2
    assert boosted.atk == base.atk
