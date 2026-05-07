from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable


HPDistribution = dict[int, Fraction]


@dataclass(frozen=True, slots=True)
class ResidualSpec:
    """One deterministic end-of-turn residual damage source."""

    kind: str
    max_hp: int
    binding_band: bool = False
    immune: bool = False


def _normalize_kind(kind: str) -> str:
    return kind.strip().lower().replace("_", "-").replace(" ", "-")


def residual_damage_amount(spec: ResidualSpec, turn_index: int) -> int:
    """Return deterministic residual damage for the given turn.

    ``turn_index`` is 1-based. Toxic uses n/16 max HP on turn n, capped at
    15/16. Other supported residuals use the Gen 9 fixed fractions listed in
    the Phase 5 scope.
    """
    if spec.max_hp < 0:
        raise ValueError("max_hp must be non-negative")
    if turn_index < 1:
        raise ValueError("turn_index must be at least 1")
    if spec.immune or spec.max_hp == 0:
        return 0

    kind = _normalize_kind(spec.kind)
    if kind == "burn":
        return spec.max_hp // 16
    if kind == "poison":
        return spec.max_hp // 8
    if kind == "toxic":
        stage = min(turn_index, 15)
        return (spec.max_hp * stage) // 16
    if kind == "leech-seed":
        return spec.max_hp // 8
    if kind == "curse":
        return spec.max_hp // 4
    if kind in {"sandstorm", "sand", "hail", "snow"}:
        return spec.max_hp // 16
    if kind in {"bind", "wrap", "fire-spin", "whirlpool", "clamp", "sand-tomb", "magma-storm", "infestation"}:
        divisor = 6 if spec.binding_band else 8
        return spec.max_hp // divisor
    raise ValueError(f"Unsupported residual kind: {spec.kind}")


def total_residual_damage(residuals: ResidualSpec | Iterable[ResidualSpec] | None, turn_index: int) -> int:
    """Return summed deterministic chip damage for a turn."""
    if residuals is None:
        return 0
    if isinstance(residuals, ResidualSpec):
        return residual_damage_amount(residuals, turn_index)
    return sum(residual_damage_amount(spec, turn_index) for spec in residuals)


def apply_residual_damage(
    hp_distribution: HPDistribution,
    residual_spec: ResidualSpec | Iterable[ResidualSpec] | None,
    turn_index: int,
) -> HPDistribution:
    """Shift a remaining-HP distribution by deterministic residual damage."""
    chip = total_residual_damage(residual_spec, turn_index)
    shifted: HPDistribution = {}
    for hp, chance in hp_distribution.items():
        next_hp = max(0, hp - chip)
        shifted[next_hp] = shifted.get(next_hp, Fraction(0, 1)) + chance
    return shifted


def hp_distribution_after_damage(
    hp_distribution: HPDistribution,
    damage_distribution: dict[int, Fraction],
) -> HPDistribution:
    """Apply move damage to a remaining-HP distribution."""
    shifted: HPDistribution = {}
    for hp, hp_chance in hp_distribution.items():
        for damage, damage_chance in damage_distribution.items():
            next_hp = max(0, hp - damage)
            shifted[next_hp] = shifted.get(next_hp, Fraction(0, 1)) + hp_chance * damage_chance
    return shifted


def ko_probability_from_hp_distribution(hp_distribution: HPDistribution) -> Fraction:
    """Return probability mass at zero HP."""
    return hp_distribution.get(0, Fraction(0, 1))
