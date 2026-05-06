from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True, slots=True)
class KOChance:
    n_hits: int
    chance: float
    description: str


def calc_ko_chance(
    rolls: list[int],
    defender_hp: int,
    defender_current_hp: int | None = None,
) -> KOChance:
    target_hp = defender_current_hp if defender_current_hp is not None else defender_hp
    if not rolls:
        return KOChance(0, 0.0, "no damage rolls")

    ohko_count = sum(1 for roll in rolls if roll >= target_hp)
    if ohko_count == len(rolls):
        return KOChance(1, 1.0, "guaranteed OHKO")
    if ohko_count > 0:
        chance = ohko_count / len(rolls)
        return KOChance(1, chance, f"{chance * 100:g}% chance to OHKO")

    two_hit_successes = sum(
        1 for first, second in product(rolls, repeat=2) if first + second >= target_hp
    )
    total = len(rolls) ** 2
    if two_hit_successes == total:
        return KOChance(2, 1.0, "guaranteed 2HKO")
    if two_hit_successes > 0:
        chance = two_hit_successes / total
        return KOChance(2, chance, f"{chance * 100:g}% chance to 2HKO")

    return KOChance(3, 0.0, "possible 3HKO or worse")
