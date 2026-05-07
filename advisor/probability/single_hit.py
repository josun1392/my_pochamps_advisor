from __future__ import annotations

from fractions import Fraction

from advisor.probability.rolls import chance_to_meet_or_exceed, roll_outcomes


def ko_chance_from_outcomes(outcomes: tuple[int, ...], target_hp: int) -> Fraction:
    """Return P(KO) from a uniform set of single-hit damage outcomes."""
    if target_hp <= 0:
        return Fraction(1, 1)
    if not outcomes:
        return Fraction(0, 1)
    return chance_to_meet_or_exceed(outcomes, target_hp)


def single_hit_ko_chance(final_damage_q12: int, target_hp: int) -> Fraction:
    """Return P(KO | one non-critical hit)."""
    return ko_chance_from_outcomes(roll_outcomes(final_damage_q12), target_hp)


def crit_integrated_ko_chance(
    final_damage_q12: int,
    target_hp: int,
    *,
    crit_rate: Fraction = Fraction(1, 24),
    crit_damage_q12: int | None = None,
) -> tuple[Fraction, Fraction]:
    """Return (P(KO), crit contribution to KO probability)."""
    if not 0 <= crit_rate <= 1:
        raise ValueError("crit_rate must be between 0 and 1")
    normal = single_hit_ko_chance(final_damage_q12, target_hp)
    crit = single_hit_ko_chance(crit_damage_q12 if crit_damage_q12 is not None else final_damage_q12, target_hp)
    crit_contribution = crit_rate * crit
    return (1 - crit_rate) * normal + crit_contribution, crit_contribution
