from __future__ import annotations

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.rng import RNG
from advisor.damage.roll import DamageRollMode


def calculate(
    ctx: DamageContext,
    *,
    roll_mode: DamageRollMode = "max",
    rng: RNG | None = None,
) -> int | tuple[int, int] | dict[int, int]:
    """Calculate damage with an opt-in roll-mode projection.

    The default is "max" for backward compatibility with callers that expect a
    single integer. Full 16-roll parity remains available through
    formula.calc_damage_rolls().
    """
    rolls = calc_damage_rolls(ctx)
    if roll_mode == "min":
        return rolls[0]
    if roll_mode == "max":
        return rolls[-1]
    if roll_mode == "deterministic":
        return (rolls[0], rolls[-1])
    if roll_mode == "probabilistic":
        if rng is None:
            rng = RNG()
        return rolls[rng.random(16)]
    if roll_mode == "distribution":
        distribution: dict[int, int] = {}
        for roll in rolls:
            distribution[roll] = distribution.get(roll, 0) + 1
        return distribution
    raise ValueError(f"unsupported damage roll mode: {roll_mode}")
