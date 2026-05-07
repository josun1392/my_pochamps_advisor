from __future__ import annotations

from dataclasses import replace

from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.rng import RNG


def _ctx(move_power: int = 90) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=move_power,
        attack_stat=120,
        defense_stat=100,
        move_type="normal",
        move_id="tackle",
        attacker_types=("normal",),
        defender_types=("electric",),
        is_physical=True,
        is_critical=False,
        is_spread=False,
        field=Field(),
    )


def test_calculator_default_no_crit() -> None:
    ctx = _ctx()

    assert calculate(ctx) == calc_damage_rolls(ctx)[-1]


def test_calculator_explicit_max_applies_1_5x() -> None:
    ctx = _ctx()

    assert calculate(ctx, crit_mode="max") == calc_damage_rolls(replace(ctx, is_critical=True))[-1]


def test_calculator_explicit_min_equals_default() -> None:
    ctx = _ctx()

    assert calculate(ctx, crit_mode="min") == calculate(ctx)


def test_calculator_probabilistic_mean_close_to_expected() -> None:
    ctx = _ctx()
    no_crit = calc_damage_rolls(ctx)[-1]
    crit = calc_damage_rolls(replace(ctx, is_critical=True))[-1]
    expected = (no_crit * 7 / 8) + (crit * 1 / 8)
    rng = RNG(20260507)
    samples = [
        calculate(ctx, crit_mode="probabilistic", crit_stage=1, rng=rng)
        for _ in range(10_000)
    ]
    mean = sum(samples) / len(samples)

    assert abs(mean - expected) <= expected * 0.01


def test_calculator_composition_order_matches_showdown() -> None:
    ctx = DamageContext(
        attacker_level=50,
        move_power=22,
        attack_stat=123,
        defense_stat=97,
        move_type="normal",
        move_id="tackle",
        attacker_types=("normal",),
        defender_types=("electric",),
        is_physical=True,
        is_critical=False,
        is_spread=False,
        field=Field(),
    )
    no_crit_min = calc_damage_rolls(ctx)[0]
    crit_before_roll = calculate(ctx, roll_mode="min", crit_mode="max")
    crit_after_roll = (no_crit_min * 3) // 2

    assert crit_before_roll == 25
    assert crit_after_roll == 24
    assert crit_before_roll != crit_after_roll


def test_calculator_crit_distribution_with_max_roll_projection() -> None:
    ctx = _ctx()
    no_crit = calc_damage_rolls(ctx)[-1]
    crit = calc_damage_rolls(replace(ctx, is_critical=True))[-1]

    assert calculate(ctx, crit_mode="distribution", crit_stage=1) == {crit: 1, no_crit: 7}
