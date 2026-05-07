from __future__ import annotations

from fractions import Fraction

import pytest

from advisor.probability import KOProbability, compute_ko_probability, guaranteed_ko_turn


def test_compute_ko_probability_returns_dataclass() -> None:
    result = compute_ko_probability(100, 100, crit_rate=Fraction(0, 1))

    assert isinstance(result, KOProbability)
    assert result.ohko == Fraction(1, 16)
    assert result.by_turn[1] == result.ohko


def test_compute_ko_probability_by_turn_up_to_four() -> None:
    result = compute_ko_probability(100, 250, crit_rate=Fraction(0, 1))

    assert set(result.by_turn) == {1, 2, 3, 4}
    assert result.by_turn[1] <= result.by_turn[2] <= result.by_turn[3] <= result.by_turn[4]


def test_compute_ko_probability_with_crit_damage() -> None:
    result = compute_ko_probability(100, 120, crit_rate=Fraction(1, 4), crit_damage_q12=150)

    assert result.ohko == Fraction(1, 4)
    assert result.crit_contribution == Fraction(1, 4)


def test_compute_ko_probability_without_crit_damage_ignores_crit_rate() -> None:
    result = compute_ko_probability(100, 120, crit_rate=Fraction(1, 1))

    assert result.ohko == 0
    assert result.crit_contribution == 0


def test_compute_ko_probability_rejects_bad_turn_count() -> None:
    with pytest.raises(ValueError):
        compute_ko_probability(100, 100, max_turns=5)


def test_compute_ko_probability_rejects_negative_damage() -> None:
    with pytest.raises(ValueError):
        compute_ko_probability(-1, 100)


def test_guaranteed_ko_turn_finds_2hko() -> None:
    assert guaranteed_ko_turn(100, 168) == 2


def test_guaranteed_ko_turn_none_when_not_guaranteed() -> None:
    assert guaranteed_ko_turn(10, 1000) is None
