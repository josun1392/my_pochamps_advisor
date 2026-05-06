from __future__ import annotations

from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.rng import RNG
from advisor.damage.roll import resolve_damage_roll


def _ctx() -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=120,
        defense_stat=100,
        move_type="fire",
        move_id="flamethrower",
        attacker_types=("fire",),
        defender_types=("electric",),
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(),
    )


def test_min_endpoint() -> None:
    assert resolve_damage_roll(100, "min") == 85


def test_max_endpoint() -> None:
    assert resolve_damage_roll(100, "max") == 100


def test_deterministic_returns_tuple() -> None:
    assert resolve_damage_roll(100, "deterministic") == (85, 100)


def test_probabilistic_seeded_reproducible() -> None:
    seq_a = [resolve_damage_roll(100, "probabilistic", RNG(20260506)) for _ in range(1)]
    seq_b = [resolve_damage_roll(100, "probabilistic", RNG(20260506)) for _ in range(1)]
    rng_a = RNG(20260506)
    rng_b = RNG(20260506)

    assert seq_a == seq_b
    assert [resolve_damage_roll(100, "probabilistic", rng_a) for _ in range(8)] == [
        resolve_damage_roll(100, "probabilistic", rng_b) for _ in range(8)
    ]


def test_distribution_shape() -> None:
    distribution = resolve_damage_roll(100, "distribution")

    assert isinstance(distribution, dict)
    assert sum(distribution.values()) == 16
    assert len(distribution) == 16
    assert set(distribution) == set(range(85, 101))


def test_distribution_mean_92_5_percent() -> None:
    distribution = resolve_damage_roll(10000, "distribution")
    total = sum(value * count for value, count in distribution.items())

    assert abs((total / 16) - 9250) <= 1


def test_probabilistic_statistical_mean() -> None:
    rng = RNG(20260506)
    samples = [resolve_damage_roll(10000, "probabilistic", rng) for _ in range(10_000)]
    mean = sum(samples) / len(samples)

    assert abs(mean - 9250) <= 100


def test_calculator_integration_default_max() -> None:
    ctx = _ctx()

    assert calculate(ctx) == calc_damage_rolls(ctx)[-1]
    assert isinstance(calculate(ctx), int)


def test_calculator_integration_explicit_deterministic() -> None:
    ctx = _ctx()
    rolls = calc_damage_rolls(ctx)

    assert calculate(ctx, roll_mode="deterministic") == (rolls[0], rolls[-1])


def test_calculator_backward_compat() -> None:
    ctx = _ctx()
    baseline = calc_damage_rolls(ctx)[-1]

    result = calculate(ctx)

    assert isinstance(result, int)
    assert result == baseline
