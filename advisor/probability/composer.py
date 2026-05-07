from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from advisor.probability.multi_hit import nhko_curve
from advisor.probability.single_hit import crit_integrated_ko_chance


@dataclass(frozen=True, slots=True)
class KOProbability:
    ohko: Fraction
    by_turn: dict[int, Fraction]
    crit_contribution: Fraction


def _crit_curve(
    final_damage_q12: int,
    target_hp: int,
    crit_rate: Fraction,
    crit_damage_q12: int | None,
    max_turns: int,
) -> tuple[dict[int, Fraction], Fraction]:
    normal_curve = nhko_curve(final_damage_q12, target_hp, max_turns)
    crit_curve = nhko_curve(crit_damage_q12 if crit_damage_q12 is not None else final_damage_q12, target_hp, max_turns)
    by_turn = {
        turn: (1 - crit_rate) * normal_curve[turn] + crit_rate * crit_curve[turn]
        for turn in normal_curve
    }
    _, crit_contribution = crit_integrated_ko_chance(
        final_damage_q12,
        target_hp,
        crit_rate=crit_rate,
        crit_damage_q12=crit_damage_q12,
    )
    return by_turn, crit_contribution


def compute_ko_probability(
    final_damage_q12: int,
    target_hp: int,
    crit_rate: Fraction = Fraction(1, 24),
    crit_damage_q12: int | None = None,
    max_turns: int = 4,
) -> KOProbability:
    """Compute KO probability by turn from a final damage base value."""
    if final_damage_q12 < 0:
        raise ValueError("final_damage_q12 must be non-negative")
    if not 1 <= max_turns <= 4:
        raise ValueError("max_turns must be in 1..4")
    if not 0 <= crit_rate <= 1:
        raise ValueError("crit_rate must be between 0 and 1")

    if crit_rate == 0 or crit_damage_q12 is None:
        by_turn = nhko_curve(final_damage_q12, target_hp, max_turns)
        crit_contribution = Fraction(0, 1)
    else:
        by_turn, crit_contribution = _crit_curve(
            final_damage_q12,
            target_hp,
            crit_rate,
            crit_damage_q12,
            max_turns,
        )
    return KOProbability(ohko=by_turn[1], by_turn=by_turn, crit_contribution=crit_contribution)


def guaranteed_ko_turn(final_damage_q12: int, target_hp: int, max_turns: int = 4) -> int | None:
    """Return the first turn with guaranteed KO, if any."""
    curve = nhko_curve(final_damage_q12, target_hp, max_turns)
    for turn, chance in curve.items():
        if chance == 1:
            return turn
    return None
