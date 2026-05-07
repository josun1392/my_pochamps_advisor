from __future__ import annotations

from fractions import Fraction

import pytest

from advisor.damage.q12 import Q12_ONE
from advisor.probability.rolls import (
    ROLL_FACTORS_Q12,
    chance_to_meet_or_exceed,
    roll_damage,
    roll_distribution,
    roll_outcomes,
)


def test_roll_factors_are_16_q12_values() -> None:
    assert len(ROLL_FACTORS_Q12) == 16
    assert ROLL_FACTORS_Q12[0] == 3482
    assert ROLL_FACTORS_Q12[-1] == Q12_ONE


def test_roll_damage_uses_q12_floor() -> None:
    assert roll_damage(100, ROLL_FACTORS_Q12[0]) == 85
    assert roll_damage(100, ROLL_FACTORS_Q12[-1]) == 100


def test_roll_outcomes_are_uniform_16_rolls() -> None:
    assert roll_outcomes(100)[0] == 85
    assert roll_outcomes(100)[-1] == 100
    assert len(roll_outcomes(100)) == 16


def test_roll_distribution_sums_to_one() -> None:
    distribution = roll_distribution(100)

    assert sum(distribution.values()) == 1
    assert all((value * 16).denominator == 1 for value in distribution.values())


def test_chance_to_meet_or_exceed_counts_uniform_outcomes() -> None:
    assert chance_to_meet_or_exceed(roll_outcomes(100), 100) == Fraction(1, 16)
    assert chance_to_meet_or_exceed(roll_outcomes(100), 85) == Fraction(1, 1)


def test_roll_damage_rejects_negative_base() -> None:
    with pytest.raises(ValueError):
        roll_damage(-1, Q12_ONE)
