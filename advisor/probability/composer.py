from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import lcm
from collections import Counter

from advisor.probability.multi_hit import (
    convolve_counts,
    multihit_damage_counts,
    multihit_damage_distribution,
    nhko_curve,
    roll_damage_counts,
    roll_damage_distribution,
)
from advisor.probability.residual import (
    HPDistribution,
    ResidualSpec,
    apply_residual_damage,
    hp_distribution_after_damage,
    ko_probability_from_hp_distribution,
    total_residual_damage,
)
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


def _weighted_damage_distribution(
    final_damage_q12: int,
    *,
    crit_rate: Fraction,
    crit_damage_q12: int | None,
    move=None,
    attacker=None,
) -> tuple[dict[int, Fraction], Fraction]:
    if not 0 <= crit_rate <= 1:
        raise ValueError("crit_rate must be between 0 and 1")
    normal = (
        multihit_damage_distribution(final_damage_q12, move, attacker)
        if move is not None
        else roll_damage_distribution(final_damage_q12)
    )
    if crit_rate == 0 or crit_damage_q12 is None:
        return normal, Fraction(0, 1)
    crit = (
        multihit_damage_distribution(crit_damage_q12, move, attacker)
        if move is not None
        else roll_damage_distribution(crit_damage_q12)
    )
    result: dict[int, Fraction] = {}
    crit_ko_mass = Fraction(0, 1)
    for damage, chance in normal.items():
        result[damage] = result.get(damage, Fraction(0, 1)) + (1 - crit_rate) * chance
    for damage, chance in crit.items():
        weighted = crit_rate * chance
        result[damage] = result.get(damage, Fraction(0, 1)) + weighted
        crit_ko_mass += weighted
    return result, crit_ko_mass


def _weighted_damage_counts(
    final_damage_q12: int,
    *,
    crit_rate: Fraction,
    crit_damage_q12: int | None,
    move=None,
    attacker=None,
) -> tuple[Counter[int], int]:
    effective_crit_rate = crit_rate if crit_damage_q12 is not None else Fraction(0, 1)
    normal_counts, normal_denominator = (
        multihit_damage_counts(final_damage_q12, move, attacker)
        if move is not None
        else roll_damage_counts(final_damage_q12)
    )
    pieces: list[tuple[Counter[int], int, int]] = [
        (
            normal_counts,
            normal_denominator * effective_crit_rate.denominator,
            effective_crit_rate.denominator - effective_crit_rate.numerator,
        )
    ]
    if effective_crit_rate:
        crit_counts, crit_denominator = (
            multihit_damage_counts(crit_damage_q12, move, attacker)
            if move is not None
            else roll_damage_counts(crit_damage_q12)
        )
        pieces.append((crit_counts, crit_denominator * effective_crit_rate.denominator, effective_crit_rate.numerator))

    common_denominator = 1
    for _, source_denominator, _ in pieces:
        common_denominator = lcm(common_denominator, source_denominator)

    result: Counter[int] = Counter()
    for counts, source_denominator, numerator in pieces:
        if numerator == 0:
            continue
        scale = common_denominator // source_denominator
        for damage, count in counts.items():
            result[damage] += count * numerator * scale
    return result, common_denominator


def compose_turn(
    hp_distribution: HPDistribution,
    damage_distribution: dict[int, Fraction],
    residuals: ResidualSpec | list[ResidualSpec] | tuple[ResidualSpec, ...] | None = None,
    *,
    turn_index: int,
) -> HPDistribution:
    """Apply one turn of move damage followed by deterministic residual chip."""
    after_damage = hp_distribution_after_damage(hp_distribution, damage_distribution)
    return apply_residual_damage(after_damage, residuals, turn_index)


def _advance_survivor_buckets(
    survivor_counts: list[int],
    damage_items: list[tuple[int, int]],
    suffix_counts: list[int],
    threshold: int,
) -> tuple[list[int], int]:
    """Advance non-KO cumulative damage buckets by one turn.

    The hot path only needs survivor buckets below the KO threshold. Keeping
    those buckets in a dense integer list avoids Counter key churn while
    preserving exact integer probability counts.
    """
    next_survivors = [0] * threshold
    ko_count = 0
    for previous_damage, previous_count in enumerate(survivor_counts):
        if previous_count == 0:
            continue
        remaining = threshold - previous_damage
        for index, (damage, damage_count) in enumerate(damage_items):
            if damage >= remaining:
                ko_count += previous_count * suffix_counts[index]
                break
            next_survivors[previous_damage + damage] += previous_count * damage_count
    return next_survivors, ko_count


def compute_ko_probability_with_effects(
    final_damage_q12: int,
    target_hp: int,
    *,
    move=None,
    attacker=None,
    residuals: ResidualSpec | list[ResidualSpec] | tuple[ResidualSpec, ...] | None = None,
    crit_rate: Fraction = Fraction(1, 24),
    crit_damage_q12: int | None = None,
    max_turns: int = 4,
) -> KOProbability:
    """Compute KO probability with optional multihit and residual damage."""
    if final_damage_q12 < 0:
        raise ValueError("final_damage_q12 must be non-negative")
    if target_hp <= 0:
        by_turn = {turn: Fraction(1, 1) for turn in range(1, max_turns + 1)}
        return KOProbability(ohko=Fraction(1, 1), by_turn=by_turn, crit_contribution=Fraction(0, 1))
    if not 1 <= max_turns <= 4:
        raise ValueError("max_turns must be in 1..4")

    damage_counts, damage_denominator = _weighted_damage_counts(
        final_damage_q12,
        crit_rate=crit_rate,
        crit_damage_q12=crit_damage_q12,
        move=move,
        attacker=attacker,
    )
    survivor_damage_counts = [1] + [0] * (target_hp - 1)
    cumulative_denominator = 1
    cumulative_chip = 0
    ko_count = 0
    damage_items = sorted(damage_counts.items())
    suffix_counts: list[int] = [0] * (len(damage_items) + 1)
    for index in range(len(damage_items) - 1, -1, -1):
        suffix_counts[index] = suffix_counts[index + 1] + damage_items[index][1]
    by_turn: dict[int, Fraction] = {}
    for turn in range(1, max_turns + 1):
        cumulative_denominator *= damage_denominator
        cumulative_chip += total_residual_damage(residuals, turn)
        threshold = target_hp - cumulative_chip
        if threshold <= 0:
            by_turn[turn] = Fraction(1, 1)
            ko_count = cumulative_denominator
            survivor_damage_counts = Counter()
        else:
            next_ko_count = ko_count * damage_denominator
            active_survivors = survivor_damage_counts[:threshold]
            next_survivors, turn_ko_count = _advance_survivor_buckets(
                active_survivors,
                damage_items,
                suffix_counts,
                threshold,
            )
            next_ko_count += turn_ko_count
            ko_count = next_ko_count
            survivor_damage_counts = next_survivors
            by_turn[turn] = Fraction(ko_count, cumulative_denominator)

    crit_contribution = Fraction(0, 1)
    if crit_rate and crit_damage_q12 is not None:
        crit_only = (
            multihit_damage_distribution(crit_damage_q12, move, attacker)
            if move is not None
            else roll_damage_distribution(crit_damage_q12)
        )
        crit_contribution = crit_rate * sum(
            chance for damage, chance in crit_only.items() if damage >= target_hp
        )
    else:
        crit_contribution = Fraction(0, 1)
    return KOProbability(ohko=by_turn[1], by_turn=by_turn, crit_contribution=crit_contribution)


def guaranteed_ko_turn(final_damage_q12: int, target_hp: int, max_turns: int = 4) -> int | None:
    """Return the first turn with guaranteed KO, if any."""
    curve = nhko_curve(final_damage_q12, target_hp, max_turns)
    for turn, chance in curve.items():
        if chance == 1:
            return turn
    return None
