from __future__ import annotations

from fractions import Fraction

import pytest

from advisor.probability.rolls import roll_outcomes
from advisor.probability.single_hit import (
    crit_integrated_ko_chance,
    ko_chance_from_outcomes,
    single_hit_ko_chance,
)


def test_ko_chance_all_rolls_ko() -> None:
    assert single_hit_ko_chance(100, 84) == 1


def test_ko_chance_no_rolls_ko() -> None:
    assert single_hit_ko_chance(100, 101) == 0


def test_ko_chance_partial_rolls() -> None:
    assert single_hit_ko_chance(100, 100) == Fraction(1, 16)


def test_zero_hp_is_already_ko() -> None:
    assert single_hit_ko_chance(100, 0) == 1


def test_empty_outcomes_no_ko() -> None:
    assert ko_chance_from_outcomes((), 1) == 0


def test_crit_integrated_no_crit_rate_matches_normal() -> None:
    chance, contribution = crit_integrated_ko_chance(100, 100, crit_rate=Fraction(0, 1), crit_damage_q12=150)

    assert chance == Fraction(1, 16)
    assert contribution == 0


def test_crit_integrated_mixes_normal_and_crit() -> None:
    chance, contribution = crit_integrated_ko_chance(100, 120, crit_rate=Fraction(1, 4), crit_damage_q12=150)

    assert chance == Fraction(1, 4)
    assert contribution == Fraction(1, 4)


def test_crit_integrated_rejects_invalid_rate() -> None:
    with pytest.raises(ValueError):
        crit_integrated_ko_chance(100, 100, crit_rate=Fraction(2, 1), crit_damage_q12=150)


def test_roll_outcomes_support_single_hit_boundary() -> None:
    outcomes = roll_outcomes(200)

    assert ko_chance_from_outcomes(outcomes, outcomes[8]) == Fraction(8, 16)
