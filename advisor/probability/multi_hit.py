from __future__ import annotations

from collections import Counter
from functools import lru_cache
from fractions import Fraction
from math import lcm

from advisor.damage.multihit import MultiHitMove, move_data_for
from advisor.probability.rolls import roll_outcomes

ProbabilityDistribution = dict[int, Fraction]


def _read_value(source, name: str, default=None):
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _normalize_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _attacker_has_ability(attacker, ability: str) -> bool:
    return _normalize_id(_read_value(attacker, "ability")) == ability


def _attacker_has_item(attacker, item: str) -> bool:
    return _normalize_id(_read_value(attacker, "item")) == item


def _fixed_distribution(value: int) -> ProbabilityDistribution:
    return {value: Fraction(1, 1)}


def _tier_a_hit_count_distribution(move: MultiHitMove, attacker) -> ProbabilityDistribution:
    if not isinstance(move.multihit, tuple):
        raise TypeError("Tier A multihit must be a range tuple")
    min_hits, max_hits = move.multihit
    if _attacker_has_ability(attacker, "skill-link"):
        return _fixed_distribution(max_hits)
    if _attacker_has_item(attacker, "loaded-dice"):
        return {4: Fraction(1, 2), 5: Fraction(1, 2)}
    if (min_hits, max_hits) != (2, 5):
        return {hits: Fraction(1, max_hits - min_hits + 1) for hits in range(min_hits, max_hits + 1)}
    return {
        2: Fraction(35, 100),
        3: Fraction(35, 100),
        4: Fraction(15, 100),
        5: Fraction(15, 100),
    }


def _tier_c_hit_count_distribution(move: MultiHitMove, attacker) -> ProbabilityDistribution:
    if not isinstance(move.multihit, int):
        raise TypeError("Tier C multihit must be a fixed integer")
    max_hits = move.multihit
    if _attacker_has_item(attacker, "loaded-dice"):
        return {hits: Fraction(1, 7) for hits in range(4, max_hits + 1)}
    if _attacker_has_ability(attacker, "skill-link"):
        return _fixed_distribution(max_hits)

    distribution: ProbabilityDistribution = {}
    accuracy = Fraction(90, 100)
    miss = 1 - accuracy
    for hits in range(1, max_hits):
        distribution[hits] = accuracy ** (hits - 1) * miss
    distribution[max_hits] = accuracy ** (max_hits - 1)
    return distribution


def compute_multihit_distribution(move, attacker=None) -> ProbabilityDistribution:
    """Return the exact hit-count distribution for a multihit move.

    Tier A range moves use Showdown's Gen 5+ 35/35/15/15 distribution.
    Skill Link is deterministic. Loaded Dice is 4/5 for Tier A and 4..10
    uniform for Tier C Population Bomb-style multiaccuracy moves.
    """
    move_data = move_data_for(move)
    multihit = move_data.multihit
    if multihit is None:
        return _fixed_distribution(1)
    if isinstance(multihit, tuple):
        return _tier_a_hit_count_distribution(move_data, attacker)
    if move_data.multiaccuracy:
        return _tier_c_hit_count_distribution(move_data, attacker)
    return _fixed_distribution(multihit)


def _normalize_distribution(distribution: ProbabilityDistribution) -> ProbabilityDistribution:
    total = sum(distribution.values(), Fraction(0, 1))
    if total <= 0:
        raise ValueError("distribution probabilities must sum to a positive value")
    return {value: chance / total for value, chance in distribution.items() if chance}


def roll_damage_distribution(final_damage_q12: int) -> ProbabilityDistribution:
    """Return one-hit 16-roll damage as an exact probability distribution."""
    counts, denominator = roll_damage_counts(final_damage_q12)
    return {damage: Fraction(count, denominator) for damage, count in sorted(counts.items())}


def roll_damage_counts(final_damage_q12: int) -> tuple[Counter[int], int]:
    """Return one-hit damage as integer counts over a common denominator."""
    counts = Counter(roll_outcomes(final_damage_q12))
    return counts, 16


def repeated_damage_counts(final_damage_q12: int, hits: int) -> tuple[Counter[int], int]:
    """Return N independent hit damage counts over denominator 16**N."""
    if hits < 1:
        raise ValueError("hits must be at least 1")
    base, base_denominator = roll_damage_counts(final_damage_q12)
    total = Counter({0: 1})
    denominator = 1
    for _ in range(hits):
        total = convolve_counts(total, base)
        denominator *= base_denominator
    return total, denominator


def _counts_to_distribution(counts: Counter[int], denominator: int) -> ProbabilityDistribution:
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    return {damage: Fraction(count, denominator) for damage, count in sorted(counts.items())}


def convolve_distributions(
    left: ProbabilityDistribution,
    right: ProbabilityDistribution,
) -> ProbabilityDistribution:
    """Convolve two Fraction-weighted integer distributions."""
    result: ProbabilityDistribution = {}
    for left_value, left_chance in left.items():
        for right_value, right_chance in right.items():
            total = left_value + right_value
            result[total] = result.get(total, Fraction(0, 1)) + left_chance * right_chance
    return result


def repeated_hit_distribution(base_dist: ProbabilityDistribution, hits: int) -> ProbabilityDistribution:
    """Return the sum distribution for N independent hits."""
    if hits < 1:
        raise ValueError("hits must be at least 1")
    normalized_base = _normalize_distribution(base_dist)
    total: ProbabilityDistribution = {0: Fraction(1, 1)}
    for _ in range(hits):
        total = convolve_distributions(total, normalized_base)
    return total


def compute_multihit_damage_distribution(
    base_dist: ProbabilityDistribution,
    hit_count_dist: ProbabilityDistribution,
) -> ProbabilityDistribution:
    """Return total damage distribution for independent per-hit rolls."""
    normalized_hits = _normalize_distribution(hit_count_dist)
    result: ProbabilityDistribution = {}
    for hits, hit_chance in normalized_hits.items():
        hit_total = repeated_hit_distribution(base_dist, hits)
        for damage, damage_chance in hit_total.items():
            result[damage] = result.get(damage, Fraction(0, 1)) + hit_chance * damage_chance
    return result


def multihit_damage_distribution(
    final_damage_q12: int,
    move,
    attacker=None,
) -> ProbabilityDistribution:
    """Return total damage distribution for one use of a multihit move."""
    counts, denominator = multihit_damage_counts(final_damage_q12, move, attacker)
    return {damage: Fraction(count, denominator) for damage, count in sorted(counts.items())}


def multihit_damage_counts(final_damage_q12: int, move, attacker=None) -> tuple[Counter[int], int]:
    """Return multihit total damage as integer counts over a common denominator."""
    move_data = move_data_for(move)
    ability = _normalize_id(_read_value(attacker, "ability"))
    item = _normalize_id(_read_value(attacker, "item"))
    return _cached_multihit_damage_counts(final_damage_q12, move_data.move_id, ability, item)


@lru_cache(maxsize=512)
def _cached_multihit_damage_counts(
    final_damage_q12: int,
    move_id: str,
    ability: str | None,
    item: str | None,
) -> tuple[Counter[int], int]:
    move = move_data_for({"move_id": move_id})
    attacker = {"ability": ability, "item": item}
    pieces: list[tuple[Counter[int], int, int]] = []
    for hits, hit_chance in compute_multihit_distribution(move, attacker).items():
        counts, damage_denominator = repeated_damage_counts(final_damage_q12, hits)
        pieces.append((counts, damage_denominator * hit_chance.denominator, hit_chance.numerator))

    common_denominator = 1
    for _, source_denominator, _ in pieces:
        common_denominator = lcm(common_denominator, source_denominator)

    result: Counter[int] = Counter()
    for counts, source_denominator, numerator in pieces:
        scale = common_denominator // source_denominator
        for damage, count in counts.items():
            result[damage] += count * numerator * scale
    return result, common_denominator


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
