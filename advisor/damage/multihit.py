from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from advisor.damage.formula import DamageContext, calc_damage_rolls


MULTIHIT_MOVES: dict[str, tuple[int, int] | int] = {
    "bullet-seed": (2, 5),
    "rock-blast": (2, 5),
    "icicle-spear": (2, 5),
}


@dataclass(frozen=True, slots=True)
class MultiHitMove:
    move_id: str
    multihit: tuple[int, int] | int | None = None


@dataclass(frozen=True, slots=True)
class MultiHitAttacker:
    ability: str | None = None


def _read_value(source, name: str, default=None):
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def multihit_for(move) -> tuple[int, int] | int | None:
    explicit = _read_value(move, "multihit")
    if explicit is not None:
        return explicit
    move_id = _read_value(move, "move_id", _read_value(move, "id", _read_value(move, "name", "")))
    return MULTIHIT_MOVES.get(str(move_id).lower())


def is_multihit(move) -> bool:
    return multihit_for(move) is not None


def resolve_hit_count(
    move,
    attacker,
    *,
    mode: Literal["min", "max", "expected"] = "min",
) -> int:
    multihit = multihit_for(move)
    if multihit is None:
        return 1
    if isinstance(multihit, int):
        return multihit

    min_hits, max_hits = multihit
    ability = _read_value(attacker, "ability")
    if ability == "skill-link":
        return max_hits
    if mode == "min":
        return min_hits
    if mode == "max":
        return max_hits
    raise NotImplementedError("expected mode reserved for future PR")


def calculate_multihit_damage(
    ctx: DamageContext,
    *,
    hit_count: int,
    roll_index: int = 0,
) -> int:
    """Calculate total damage for one roll index by summing each hit."""
    total = 0
    for hit_idx in range(hit_count):
        del hit_idx
        hit_rolls = calc_damage_rolls(ctx)
        total += hit_rolls[roll_index]
    return total


def calc_multihit_damage_rolls(ctx: DamageContext, *, hit_count: int) -> list[int]:
    """Return 16 total multihit damage rolls, summed hit-by-hit."""
    return [
        calculate_multihit_damage(ctx, hit_count=hit_count, roll_index=roll_index)
        for roll_index in range(16)
    ]
