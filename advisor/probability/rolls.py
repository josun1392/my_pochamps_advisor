from __future__ import annotations

from collections import Counter
from fractions import Fraction

from advisor.damage.q12 import Q12_ONE


ROLL_PERCENTAGES: tuple[int, ...] = tuple(range(85, 101))
ROLL_FACTORS_Q12: tuple[int, ...] = tuple((percent * Q12_ONE + 50) // 100 for percent in ROLL_PERCENTAGES)


def roll_damage(final_damage_q12: int, roll_factor_q12: int) -> int:
    """Apply one 16-roll factor to an integer damage value."""
    if final_damage_q12 < 0:
        raise ValueError("final_damage_q12 must be non-negative")
    return (final_damage_q12 * roll_factor_q12) // Q12_ONE


def roll_outcomes(final_damage_q12: int) -> tuple[int, ...]:
    """Return the 16 uniformly likely integer damage rolls."""
    return tuple(roll_damage(final_damage_q12, factor) for factor in ROLL_FACTORS_Q12)


def roll_distribution(final_damage_q12: int) -> dict[int, Fraction]:
    """Return a probability distribution for the 16 damage rolls."""
    counts = Counter(roll_outcomes(final_damage_q12))
    return {damage: Fraction(count, 16) for damage, count in sorted(counts.items())}


def chance_to_meet_or_exceed(outcomes: tuple[int, ...], threshold: int) -> Fraction:
    """Return P(outcome >= threshold) for equally likely outcomes."""
    if threshold <= 0:
        return Fraction(1, 1)
    return Fraction(sum(damage >= threshold for damage in outcomes), len(outcomes))
