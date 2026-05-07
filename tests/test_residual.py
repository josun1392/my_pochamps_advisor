from __future__ import annotations

from fractions import Fraction

import pytest

from advisor.probability.composer import compose_turn, compute_ko_probability_with_effects
from advisor.probability.residual import (
    ResidualSpec,
    apply_residual_damage,
    hp_distribution_after_damage,
    residual_damage_amount,
    total_residual_damage,
)


def test_burn_residual_is_one_sixteenth() -> None:
    assert residual_damage_amount(ResidualSpec("burn", max_hp=160), 1) == 10


def test_poison_residual_is_one_eighth() -> None:
    assert residual_damage_amount(ResidualSpec("poison", max_hp=160), 1) == 20


def test_toxic_residual_scales_with_turn() -> None:
    assert residual_damage_amount(ResidualSpec("toxic", max_hp=160), 1) == 10
    assert residual_damage_amount(ResidualSpec("toxic", max_hp=160), 3) == 30


def test_toxic_residual_caps_at_fifteen_sixteenths() -> None:
    assert residual_damage_amount(ResidualSpec("toxic", max_hp=160), 20) == 150


@pytest.mark.parametrize("kind", ["sandstorm", "sand", "hail", "snow"])
def test_weather_residual_is_one_sixteenth(kind: str) -> None:
    assert residual_damage_amount(ResidualSpec(kind, max_hp=160), 1) == 10


def test_binding_band_residual_is_one_sixth() -> None:
    assert residual_damage_amount(ResidualSpec("bind", max_hp=180, binding_band=True), 1) == 30


def test_residual_immune_returns_zero() -> None:
    assert residual_damage_amount(ResidualSpec("sandstorm", max_hp=160, immune=True), 1) == 0


def test_residual_rejects_bad_turn_index() -> None:
    with pytest.raises(ValueError):
        residual_damage_amount(ResidualSpec("burn", max_hp=160), 0)


def test_total_residual_damage_sums_multiple_specs() -> None:
    residuals = [ResidualSpec("burn", max_hp=160), ResidualSpec("poison", max_hp=160)]

    assert total_residual_damage(residuals, 1) == 30


def test_apply_residual_damage_shifts_hp_distribution() -> None:
    result = apply_residual_damage({50: Fraction(1, 2), 10: Fraction(1, 2)}, ResidualSpec("burn", max_hp=160), 1)

    assert result == {40: Fraction(1, 2), 0: Fraction(1, 2)}


def test_hp_distribution_after_damage_convolves_hp_and_damage() -> None:
    result = hp_distribution_after_damage(
        {100: Fraction(1, 1)},
        {40: Fraction(1, 4), 60: Fraction(3, 4)},
    )

    assert result == {60: Fraction(1, 4), 40: Fraction(3, 4)}


def test_compose_turn_applies_damage_then_chip() -> None:
    result = compose_turn(
        {100: Fraction(1, 1)},
        {80: Fraction(1, 1)},
        ResidualSpec("burn", max_hp=160),
        turn_index=1,
    )

    assert result == {10: Fraction(1, 1)}


def test_compose_turn_can_ko_with_chip_after_non_ko_damage() -> None:
    result = compose_turn(
        {100: Fraction(1, 1)},
        {95: Fraction(1, 1)},
        ResidualSpec("burn", max_hp=160),
        turn_index=1,
    )

    assert result == {0: Fraction(1, 1)}


def test_compute_ko_probability_with_chip_only_finds_second_turn_ko() -> None:
    result = compute_ko_probability_with_effects(
        0,
        20,
        residuals=ResidualSpec("burn", max_hp=160),
        crit_rate=Fraction(0, 1),
        max_turns=2,
    )

    assert result.by_turn[1] == 0
    assert result.by_turn[2] == 1


def test_compute_ko_probability_with_toxic_progression() -> None:
    result = compute_ko_probability_with_effects(
        0,
        60,
        residuals=ResidualSpec("toxic", max_hp=160),
        crit_rate=Fraction(0, 1),
        max_turns=3,
    )

    assert result.by_turn[1] == 0
    assert result.by_turn[2] == 0
    assert result.by_turn[3] == 1
