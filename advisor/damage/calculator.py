from __future__ import annotations

from dataclasses import replace

from advisor.damage.crit import CritRollMode, resolve_crit_roll
from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.rng import RNG
from advisor.damage.roll import DamageRollMode


def _project_rolls(
    rolls: list[int],
    roll_mode: DamageRollMode,
    rng: RNG | None,
) -> int | tuple[int, int] | dict[int, int]:
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


def calculate(
    ctx: DamageContext,
    *,
    roll_mode: DamageRollMode = "max",
    crit_mode: CritRollMode = "min",
    crit_stage: int = 0,
    rng: RNG | None = None,
) -> int | tuple[int, int] | dict[int, int]:
    """Calculate damage with an opt-in roll-mode projection.

    The roll default is "max" and the crit default is "min" for backward
    compatibility with callers that expect the historical non-crit max roll.
    Full 16-roll parity remains available through formula.calc_damage_rolls().
    """
    crit = resolve_crit_roll(
        crit_stage,
        crit_mode,
        rng,
        defender_state=ctx,
        field_state=ctx.field,
    )
    if isinstance(crit, bool):
        rolls = calc_damage_rolls(replace(ctx, is_critical=crit))
        return _project_rolls(rolls, roll_mode, rng)
    if isinstance(crit, tuple):
        no_crit_rolls = calc_damage_rolls(replace(ctx, is_critical=crit[0]))
        crit_rolls = calc_damage_rolls(replace(ctx, is_critical=crit[1]))
        return (
            _project_rolls(no_crit_rolls, roll_mode, rng),  # type: ignore[arg-type]
            _project_rolls(crit_rolls, roll_mode, rng),  # type: ignore[arg-type]
        )
    distribution: dict[int, int] = {}
    for is_crit, count in crit.items():
        rolls = calc_damage_rolls(replace(ctx, is_critical=is_crit))
        projected = _project_rolls(rolls, roll_mode, rng)
        if not isinstance(projected, int):
            raise ValueError("crit distribution requires an integer roll projection")
        distribution[projected] = distribution.get(projected, 0) + count
    return distribution
