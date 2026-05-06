from __future__ import annotations

import pytest

from advisor.damage.stats import (
    StatBlock,
    StatInputs,
    apply_boosts,
    calc_stat_champions,
    calc_stat_gen9,
    final_stats,
    nature_from_name,
)


GARCHOMP_BASE = StatBlock(108, 130, 95, 80, 85, 102)
ZERO = StatBlock(0, 0, 0, 0, 0, 0)
GEN9_IVS = StatBlock(31, 31, 31, 31, 31, 31)


def test_gen9_garchomp_adamant_atk() -> None:
    stats = final_stats(
        StatInputs(
            base=GARCHOMP_BASE,
            evs=StatBlock(0, 252, 0, 0, 0, 0),
            ivs=GEN9_IVS,
            nature_plus="atk",
            nature_minus="spa",
            level=50,
            rule_set="gen9",
        )
    )

    assert stats.atk == 200


def test_gen9_garchomp_neutral_atk() -> None:
    assert calc_stat_gen9(130, 252, 31, 50, 1.0, is_hp=False) == 182


def test_gen9_level_100_hp() -> None:
    assert calc_stat_gen9(108, 252, 31, 100, 1.0, is_hp=True) == 420


def test_champions_ignores_iv() -> None:
    low_iv = calc_stat_champions(130, 32, 50, 1.0, is_hp=False)
    high_iv_equivalent = calc_stat_gen9(130, 32, 31, 50, 1.0, is_hp=False)

    assert low_iv == high_iv_equivalent


def test_champions_ev_cap() -> None:
    with pytest.raises(ValueError):
        calc_stat_champions(130, 33, 50, 1.0, is_hp=False)


def test_apply_boost_plus_two() -> None:
    assert apply_boosts(100, 2) == 200


def test_apply_boost_minus_two() -> None:
    assert apply_boosts(100, -2) == 50


def test_apply_boost_plus_six() -> None:
    assert apply_boosts(100, 6) == 400


def test_apply_boost_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        apply_boosts(100, 7)


def test_nature_from_name() -> None:
    assert nature_from_name("Jolly") == ("spe", "spa")


def test_final_stats_champions_mode() -> None:
    stats = final_stats(
        StatInputs(
            base=GARCHOMP_BASE,
            evs=StatBlock(32, 32, 32, 32, 32, 32),
            ivs=ZERO,
            nature_plus=None,
            nature_minus=None,
            level=50,
            rule_set="champions",
        )
    )

    assert stats.hp == calc_stat_gen9(108, 32, 31, 50, 1.0, is_hp=True)
