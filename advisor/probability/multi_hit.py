from __future__ import annotations

from collections import Counter
from fractions import Fraction

from advisor.probability.rolls import roll_outcomes


def convolve_counts(left: Counter[int], right: Counter[int]) -> Counter[int]:
    """Convolve two integer damage count distributions."""
    result: Counter[int] = Counter()
    for left_damage, left_count in left.items():
        for right_damage, right_count in right.items():
            result[left_damage + right_damage] += left_count * right_count
    return result


def summed_damage_counts(final_damage_q12: int, hits: int) -> Counter[int]:
    """Return count distribution for the sum of N independent 16-roll hits."""
    if hits < 1:
        raise ValueError("hits must be at least 1")
    if hits > 4:
        raise ValueError("hits above 4 are outside Phase 4 scope")
    base = Counter(roll_outcomes(final_damage_q12))
    total = Counter({0: 1})
    for _ in range(hits):
        total = convolve_counts(total, base)
    return total


def nhko_chance(final_damage_q12: int, target_hp: int, hits: int) -> Fraction:
    """Return P(total damage across N independent hits >= target HP)."""
    if target_hp <= 0:
        return Fraction(1, 1)
    counts = summed_damage_counts(final_damage_q12, hits)
    favorable = sum(count for damage, count in counts.items() if damage >= target_hp)
    total = sum(counts.values())
    return Fraction(favorable, total)


def nhko_curve(final_damage_q12: int, target_hp: int, max_turns: int = 4) -> dict[int, Fraction]:
    """Return cumulative KO probability by turn for repeated identical hits."""
    if not 1 <= max_turns <= 4:
        raise ValueError("max_turns must be in 1..4")
    return {turn: nhko_chance(final_damage_q12, target_hp, turn) for turn in range(1, max_turns + 1)}
