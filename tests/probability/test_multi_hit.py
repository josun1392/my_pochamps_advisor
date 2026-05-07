from __future__ import annotations

from fractions import Fraction

import pytest

from advisor.probability.multi_hit import nhko_chance, nhko_curve, summed_damage_counts


def test_summed_damage_counts_one_hit_total_count() -> None:
    assert sum(summed_damage_counts(100, 1).values()) == 16


def test_summed_damage_counts_two_hits_total_count() -> None:
    assert sum(summed_damage_counts(100, 2).values()) == 256


def test_summed_damage_counts_four_hits_total_count() -> None:
    assert sum(summed_damage_counts(100, 4).values()) == 65536


def test_nhko_chance_guaranteed_two_hit() -> None:
    assert nhko_chance(100, 168, 2) == 1


def test_nhko_chance_impossible_two_hit() -> None:
    assert nhko_chance(100, 201, 2) == 0


def test_nhko_curve_is_monotonic() -> None:
    curve = nhko_curve(100, 250, 4)

    assert curve[1] <= curve[2] <= curve[3] <= curve[4]


def test_nhko_curve_rejects_max_turns_above_four() -> None:
    with pytest.raises(ValueError):
        nhko_curve(100, 100, 5)


def test_summed_damage_counts_rejects_zero_hits() -> None:
    with pytest.raises(ValueError):
        summed_damage_counts(100, 0)


def test_three_hit_fraction_exactness() -> None:
    chance = nhko_chance(100, 300, 3)

    assert chance == Fraction(1, 4096)
