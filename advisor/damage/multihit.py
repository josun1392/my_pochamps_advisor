from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from advisor.damage.formula import DamageContext, calc_damage_rolls


@dataclass(frozen=True, slots=True)
class MultiHitMove:
    move_id: str
    multihit: tuple[int, int] | int | None = None
    base_power: int | None = None
    bp_escalation: bool = False
    multiaccuracy: bool = False


@dataclass(frozen=True, slots=True)
class MultiHitAttacker:
    ability: str | None = None
    item: str | None = None


MULTIHIT_MOVES: dict[str, MultiHitMove] = {
    "bullet-seed": MultiHitMove("bullet-seed", multihit=(2, 5), base_power=25),
    "rock-blast": MultiHitMove("rock-blast", multihit=(2, 5), base_power=25),
    "icicle-spear": MultiHitMove("icicle-spear", multihit=(2, 5), base_power=25),
    "triple-kick": MultiHitMove("triple-kick", multihit=3, base_power=10, bp_escalation=True),
    "triple-axel": MultiHitMove("triple-axel", multihit=3, base_power=20, bp_escalation=True),
    "population-bomb": MultiHitMove(
        "population-bomb",
        multihit=10,
        base_power=20,
        multiaccuracy=True,
    ),
}


def _read_value(source, name: str, default=None):
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _move_id_for(move) -> str:
    return str(_read_value(move, "move_id", _read_value(move, "id", _read_value(move, "name", "")))).lower()


def move_data_for(move) -> MultiHitMove:
    move_id = _move_id_for(move)
    registered = MULTIHIT_MOVES.get(move_id)
    explicit_multihit = _read_value(move, "multihit")
    explicit_base_power = _read_value(move, "base_power")
    return MultiHitMove(
        move_id=move_id,
        multihit=explicit_multihit if explicit_multihit is not None else registered.multihit if registered else None,
        base_power=explicit_base_power
        if explicit_base_power is not None
        else registered.base_power if registered else None,
        bp_escalation=bool(_read_value(move, "bp_escalation") or (registered and registered.bp_escalation)),
        multiaccuracy=bool(_read_value(move, "multiaccuracy") or (registered and registered.multiaccuracy)),
    )


def multihit_for(move) -> tuple[int, int] | int | None:
    return move_data_for(move).multihit


def is_multihit(move) -> bool:
    return multihit_for(move) is not None


def get_escalated_bp(move, hit_index: int, *, base_power: int | None = None) -> int:
    """Return per-hit BP for Triple Axel/Kick style BP escalation."""
    move_data = move_data_for(move)
    resolved_base_power = base_power if base_power is not None else move_data.base_power
    if resolved_base_power is None:
        raise ValueError(f"Missing base power for {move_data.move_id}")
    if not move_data.bp_escalation:
        return resolved_base_power
    return resolved_base_power * (hit_index + 1)


def _resolve_tier_a(
    multihit: tuple[int, int],
    attacker,
    mode: Literal["min", "max", "expected"],
) -> int:
    """Resolve range multihit moves such as Bullet Seed and Rock Blast."""
    min_hits, max_hits = multihit
    ability = _read_value(attacker, "ability")
    if ability == "skill-link":
        return max_hits
    item = _read_value(attacker, "item")
    if item == "loaded-dice":
        if mode == "min":
            return 4
        if mode == "max":
            return 5
        raise NotImplementedError(
            "Loaded Dice expected distribution reserved for PR #3.4-D"
        )
    if mode == "min":
        return min_hits
    if mode == "max":
        return max_hits
    raise NotImplementedError("Multihit expected distribution reserved for PR #3.4-D")


def _resolve_tier_c(
    move: MultiHitMove,
    attacker,
    mode: Literal["min", "max", "expected"],
) -> int:
    """Resolve multiaccuracy fixed-10 hit moves such as Population Bomb."""
    if not isinstance(move.multihit, int):
        raise TypeError("Tier C multihit must be a fixed integer")

    ability = _read_value(attacker, "ability")
    if ability == "skill-link":
        return move.multihit

    item = _read_value(attacker, "item")
    if item == "loaded-dice":
        if mode == "min":
            return 4
        if mode == "max":
            return move.multihit
        raise NotImplementedError(
            "Loaded Dice + multiaccuracy probabilistic sampling reserved for PR #3.4-D"
        )

    if mode == "min":
        return 1
    if mode == "max":
        return move.multihit
    raise NotImplementedError("Multiaccuracy probabilistic sampling reserved for PR #3.4-D")


def resolve_hit_count(
    move,
    attacker,
    *,
    mode: Literal["min", "max", "expected"] = "min",
) -> int:
    """
    Hit-count resolution priority:
      1. Skill Link (ability) -> max hits for range multihit.
      2. Loaded Dice (item) -> 4 min / 5 max for range multihit.
      3. Default -> move min / max.

    Ability beats item because Pokemon Showdown evaluates Skill Link before
    Loaded Dice when both are present.
    """
    move_data = move_data_for(move)
    multihit = move_data.multihit
    if multihit is None:
        return 1
    if isinstance(multihit, int) and move_data.multiaccuracy:
        return _resolve_tier_c(move_data, attacker, mode)
    if isinstance(multihit, int):
        return multihit

    return _resolve_tier_a(multihit, attacker, mode)


def calculate_multihit_damage(
    ctx: DamageContext,
    *,
    hit_count: int,
    roll_index: int = 0,
    move=None,
) -> int:
    """Calculate total damage for one roll index by summing each hit."""
    total = 0
    for hit_idx in range(hit_count):
        if move is None:
            hit_ctx = ctx
        else:
            hit_ctx = replace(
                ctx,
                move_power=get_escalated_bp(move, hit_idx, base_power=ctx.move_power),
            )
        hit_rolls = calc_damage_rolls(hit_ctx)
        total += hit_rolls[roll_index]
    return total


def calc_multihit_damage_rolls(ctx: DamageContext, *, hit_count: int, move=None) -> list[int]:
    """Return 16 total multihit damage rolls, summed hit-by-hit."""
    return [
        calculate_multihit_damage(ctx, hit_count=hit_count, roll_index=roll_index, move=move)
        for roll_index in range(16)
    ]
