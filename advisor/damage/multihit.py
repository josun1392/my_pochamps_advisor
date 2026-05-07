from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.rng import RNG


HitCountMode = Literal["min", "max", "deterministic", "probabilistic", "expected"]


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
    "tail-slap": MultiHitMove("tail-slap", multihit=(2, 5), base_power=25),
    "pin-missile": MultiHitMove("pin-missile", multihit=(2, 5), base_power=25),
    "water-shuriken": MultiHitMove("water-shuriken", multihit=(2, 5), base_power=15),
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
    mode: HitCountMode,
    rng: RNG | None = None,
) -> int | tuple[int, int]:
    """Resolve range multihit moves such as Bullet Seed and Rock Blast."""
    min_hits, max_hits = multihit
    ability = _read_value(attacker, "ability")
    if ability == "skill-link":
        return (max_hits, max_hits) if mode == "deterministic" else max_hits
    item = _read_value(attacker, "item")
    if item == "loaded-dice":
        if mode == "min":
            return 4
        if mode == "max":
            return 5
        if mode == "deterministic":
            return (4, 5)
        if mode in {"probabilistic", "expected"}:
            if rng is None:
                rng = RNG()
            # Showdown: if initial 2-5 roll is below 4 and Loaded Dice is held,
            # targetHits = 5 - random(2), so the deterministic distribution is 4/5.
            # Source: sim/battle-actions.ts lines 865-867.
            return 4 + rng.random(2)
        raise NotImplementedError(
            "Loaded Dice expected distribution reserved for PR #3.4-D"
        )
    if mode == "min":
        return min_hits
    if mode == "max":
        return max_hits
    if mode == "deterministic":
        return (min_hits, max_hits)
    if mode in {"probabilistic", "expected"}:
        if rng is None:
            rng = RNG()
        # Showdown samples duplicate entries:
        # [2 x7, 3 x7, 4 x3, 5 x3], i.e. 35/35/15/15.
        # Source: sim/battle-actions.ts lines 864-865.
        return [2, 3, 4, 5][rng.weighted_choice([35, 35, 15, 15])]
    raise ValueError(f"Unsupported hit-count mode: {mode}")


def _resolve_tier_c(
    move: MultiHitMove,
    attacker,
    mode: HitCountMode,
    rng: RNG | None = None,
) -> int | tuple[int, int]:
    """Resolve multiaccuracy fixed-10 hit moves such as Population Bomb.

    Showdown order matters here: Skill Link removes multiaccuracy via
    onModifyMove, then Loaded Dice's hit-loop branch still runs because it only
    checks ``targetHits === 10 && hasItem('loadeddice')``. Source:
    sim/battle-actions.ts line 876, Pokemon Showdown master.
    """
    if not isinstance(move.multihit, int):
        raise TypeError("Tier C multihit must be a fixed integer")

    item = _read_value(attacker, "item")
    if item == "loaded-dice":
        if mode == "min":
            return 4
        if mode == "max":
            return move.multihit
        if mode == "deterministic":
            return (4, move.multihit)
        if mode in {"probabilistic", "expected"}:
            if rng is None:
                rng = RNG()
            # Showdown: if targetHits === 10 and Loaded Dice is held,
            # targetHits -= random(7), producing a uniform 4..10.
            # Source: sim/battle-actions.ts line 876.
            return move.multihit - rng.random(7)
        raise ValueError(f"Unsupported hit-count mode: {mode}")

    ability = _read_value(attacker, "ability")
    if ability == "skill-link":
        return (move.multihit, move.multihit) if mode == "deterministic" else move.multihit

    if mode == "min":
        return 1
    if mode == "max":
        return move.multihit
    if mode == "deterministic":
        return (1, move.multihit)
    if mode in {"probabilistic", "expected"}:
        if rng is None:
            rng = RNG()
        hits = 1
        # Post-connect model: hit 1 has landed; hits 2..10 independently roll
        # move accuracy and stop on the first miss. Neutral Population Bomb uses
        # 90 accuracy. Accuracy modifiers are reserved for a later layer.
        # Source: sim/battle-actions.ts lines 907-933.
        for _ in range(move.multihit - 1):
            if rng.random(100) < 90:
                hits += 1
            else:
                break
        return hits
    raise ValueError(f"Unsupported hit-count mode: {mode}")


def resolve_hit_count(
    move,
    attacker,
    *,
    mode: HitCountMode = "min",
    rng: RNG | None = None,
) -> int | tuple[int, int]:
    """Resolve the number of hits for a multihit move.

    This function uses a post-connect model: the move has already passed the
    initial accuracy check. Default Tier C minimum is therefore 1, not 0.

    Tier A: range multihit tuple, e.g. Bullet Seed (2, 5).
    Tier B: fixed int multihit, e.g. Triple Axel/Kick.
    Tier C: fixed int multihit with multiaccuracy, e.g. Population Bomb.

    Tier A Skill Link beats Loaded Dice because Showdown's onModifyMove turns
    the multihit array into max int before the Loaded Dice ``targetHits < 4``
    branch can apply.

    Tier C Skill Link does not block Loaded Dice. Skill Link removes
    multiaccuracy, but Loaded Dice later checks only
    ``targetHits === 10 && hasItem('loadeddice')`` in the hit loop. Source:
    sim/battle-actions.ts line 876, Pokemon Showdown master.
    """
    move_data = move_data_for(move)
    multihit = move_data.multihit
    if multihit is None:
        return (1, 1) if mode == "deterministic" else 1
    if isinstance(multihit, int) and move_data.multiaccuracy:
        return _resolve_tier_c(move_data, attacker, mode, rng)
    if isinstance(multihit, int):
        return (multihit, multihit) if mode == "deterministic" else multihit

    return _resolve_tier_a(multihit, attacker, mode, rng)


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
