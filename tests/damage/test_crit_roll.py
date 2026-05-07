from __future__ import annotations

from advisor.damage.crit import CritState, apply_crit_modifier, crit_probability, resolve_crit_roll
from advisor.damage.rng import RNG


def test_min_returns_false() -> None:
    assert resolve_crit_roll(stage=2, mode="min") is False


def test_max_returns_true_unless_blocked() -> None:
    assert resolve_crit_roll(stage=0, mode="max") is True


def test_max_blocked_by_battle_armor() -> None:
    assert resolve_crit_roll(stage=3, mode="max", defender_state=CritState(ability="battle-armor")) is False


def test_deterministic_returns_pair() -> None:
    assert resolve_crit_roll(stage=1, mode="deterministic") == (False, True)


def test_probabilistic_seeded_reproducible() -> None:
    rng_a = RNG(20260507)
    rng_b = RNG(20260507)

    assert [resolve_crit_roll(1, "probabilistic", rng_a) for _ in range(1000)] == [
        resolve_crit_roll(1, "probabilistic", rng_b) for _ in range(1000)
    ]


def test_distribution_stage_0() -> None:
    assert resolve_crit_roll(stage=0, mode="distribution") == {True: 1, False: 23}


def test_distribution_stage_1() -> None:
    assert resolve_crit_roll(stage=1, mode="distribution") == {True: 1, False: 7}


def test_distribution_stage_2() -> None:
    assert resolve_crit_roll(stage=2, mode="distribution") == {True: 1, False: 1}


def test_distribution_stage_3_guaranteed() -> None:
    assert resolve_crit_roll(stage=3, mode="distribution") == {True: 1, False: 0}


def test_probabilistic_statistical_rate_stage_0() -> None:
    rng = RNG(20260507)
    crits = sum(bool(resolve_crit_roll(0, "probabilistic", rng)) for _ in range(24_000))

    assert abs(crits - 1000) <= 1200 * 0.05


def test_probabilistic_statistical_rate_stage_1() -> None:
    rng = RNG(20260507)
    crits = sum(bool(resolve_crit_roll(1, "probabilistic", rng)) for _ in range(8_000))

    assert abs(crits - 1000) <= 1000 * 0.05


def test_crit_probability_clamps_stage_three_plus() -> None:
    assert crit_probability(99).numerator == 1
    assert crit_probability(99).denominator == 1


def test_apply_crit_modifier_gen_six_plus() -> None:
    assert apply_crit_modifier(101, True) == 151
    assert apply_crit_modifier(101, False) == 101
