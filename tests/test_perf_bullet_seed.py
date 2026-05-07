from __future__ import annotations

from fractions import Fraction
import statistics
import time

import pytest

from advisor.damage.multihit import MULTIHIT_MOVES
from advisor.probability.composer import (
    _weighted_damage_counts,
    compute_ko_probability_with_effects,
)
from advisor.probability.residual import ResidualSpec

pytestmark = pytest.mark.slow


def _bullet_seed_worst_case():
    return compute_ko_probability_with_effects(
        100,
        900,
        move=MULTIHIT_MOVES["bullet-seed"],
        attacker={},
        residuals=ResidualSpec("burn", 320),
        crit_rate=Fraction(1, 24),
        crit_damage_q12=150,
        max_turns=4,
    )


def _measure_bullet_seed_with_crit() -> float:
    """Single Bullet Seed worst-case measurement in milliseconds."""
    start = time.perf_counter()
    _bullet_seed_worst_case()
    return (time.perf_counter() - start) * 1000


def test_bullet_seed_default_with_crit_perf_under_15ms() -> None:
    """Perf regression pin for clean `pytest -m slow` runs."""
    _measure_bullet_seed_with_crit()

    samples = [_measure_bullet_seed_with_crit() for _ in range(3)]
    median_ms = statistics.median(samples)

    assert median_ms < 15.0, (
        f"Bullet seed worst case regressed: median={median_ms:.3f}ms, "
        f"samples={[f'{sample:.3f}' for sample in samples]}, threshold=15ms"
    )


def test_bullet_seed_probability_invariant() -> None:
    """Weighted count buckets must still represent exactly one outcome space."""
    counts, denominator = _weighted_damage_counts(
        100,
        crit_rate=Fraction(1, 24),
        crit_damage_q12=150,
        move=MULTIHIT_MOVES["bullet-seed"],
        attacker={},
    )

    assert Fraction(sum(counts.values()), denominator) == Fraction(1, 1)
