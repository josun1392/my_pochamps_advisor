from __future__ import annotations

from typing import Literal

from advisor.damage.rng import RNG


DamageRollMode = Literal["min", "max", "deterministic", "probabilistic", "distribution"]


def _roll_value(base_damage: int, random_factor: int) -> int:
    return (base_damage * random_factor) // 100


def resolve_damage_roll(
    base_damage: int,
    mode: DamageRollMode,
    rng: RNG | None = None,
) -> int | tuple[int, int] | dict[int, int]:
    """Resolve Pokemon's 16-value damage roll layer.

    Showdown applies ``floor(base * (85 + random(16)) / 100)``.
    Source: pokemon-showdown/sim/battle-actions.ts randomizer(), lines 2404-2406.
    """
    if base_damage < 0:
        raise ValueError("base_damage must be non-negative")
    if mode == "min":
        return _roll_value(base_damage, 85)
    if mode == "max":
        return base_damage
    if mode == "deterministic":
        return (_roll_value(base_damage, 85), base_damage)
    if mode == "probabilistic":
        if rng is None:
            rng = RNG()
        return _roll_value(base_damage, 85 + rng.random(16))
    if mode == "distribution":
        distribution: dict[int, int] = {}
        for random_factor in range(85, 101):
            value = _roll_value(base_damage, random_factor)
            distribution[value] = distribution.get(value, 0) + 1
        return distribution
    raise ValueError(f"unsupported damage roll mode: {mode}")
