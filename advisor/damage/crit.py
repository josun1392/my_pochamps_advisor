from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from advisor.damage.modifiers.abilities import apply_sniper
from advisor.damage.modifiers._q12 import MUL_1_5
from advisor.damage.q12 import Q12_ONE
from advisor.damage.rng import RNG


CritRollMode = Literal["min", "max", "deterministic", "probabilistic", "distribution"]
CRIT_GUARANTEED_STAGE = 3

_HIGH_CRIT_MOVES = {
    "slash",
    "stone-edge",
    "leaf-blade",
    "night-slash",
    "cross-poison",
    "shadow-claw",
    "psycho-cut",
    "razor-leaf",
    "crabhammer",
    "karate-chop",
    "air-cutter",
    "attack-order",
    "spacial-rend",
}

_ALWAYS_CRIT_MOVES = {
    "storm-throw",
    "frost-breath",
    "surging-strikes",
    "wicked-blow",
    "flower-trick",
    "zippy-zap",
}

_STAGE_ONE_ITEMS = {"razor-claw", "scope-lens"}
_CRIT_BLOCKING_ABILITIES = {"battle-armor", "shell-armor"}


@dataclass(frozen=True, slots=True)
class CritState:
    ability: str | None = None
    item: str | None = None
    species: str = ""
    status: str | None = None
    types: tuple[str, ...] = ()
    volatiles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MoveCritState:
    move_id: str = ""
    high_crit_ratio: bool = False
    always_crit: bool = False
    crit_stage_bonus: int = 0


def move_crit_rule(move_id: str) -> str:
    """Return the engine's static move rule classification for one move id."""
    normalized = _normalize(move_id)
    if normalized in _ALWAYS_CRIT_MOVES:
        return "always-crit"
    if normalized in _HIGH_CRIT_MOVES:
        return "high-crit"
    return "base"


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _read_value(state: Any, *names: str) -> Any:
    if state is None:
        return None
    for name in names:
        if isinstance(state, dict) and name in state:
            return state[name]
        if hasattr(state, name):
            return getattr(state, name)
    return None


def _ability_id(state: Any) -> str:
    ability = _read_value(state, "ability", "ability_id", "attacker_ability", "defender_ability")
    if hasattr(ability, "ability_id"):
        ability = ability.ability_id
    return _normalize(ability)


def _item_id(state: Any) -> str:
    item = _read_value(state, "item", "item_id", "attacker_item")
    if hasattr(item, "item_id"):
        item = item.item_id
    return _normalize(item)


def _status_id(state: Any) -> str:
    return _normalize(_read_value(state, "status", "defender_status"))


def _species_id(state: Any) -> str:
    return _normalize(_read_value(state, "species", "species_id", "attacker_species"))


def _types(state: Any) -> tuple[str, ...]:
    raw = _read_value(state, "types", "attacker_types") or ()
    return tuple(_normalize(t) for t in raw)


def _volatiles(state: Any) -> set[str]:
    raw = _read_value(state, "volatiles", "volatile_status", "attacker_volatiles") or ()
    if isinstance(raw, dict):
        return {_normalize(k) for k, value in raw.items() if value}
    if isinstance(raw, str):
        return {_normalize(raw)}
    return {_normalize(value) for value in raw}


def _move_id(move_state: Any) -> str:
    return _normalize(_read_value(move_state, "move_id", "id", "name"))


def _flag(move_state: Any, *names: str) -> bool:
    return any(bool(_read_value(move_state, name)) for name in names)


def resolve_crit_stage(attacker_state: Any, move_state: Any, defender_state: Any | None = None) -> int:
    """Return the Gen 9 critical-hit stage after attacker, move, and target effects.

    Stage probabilities are 0 -> 1/24, 1 -> 1/8, 2 -> 1/2, and 3+ ->
    guaranteed. Always-crit moves and Merciless raise the result to at least
    stage 3; defender-side blockers are applied by resolve_crit_roll().
    """
    move_id = _move_id(move_state)
    if move_id in _ALWAYS_CRIT_MOVES or _flag(move_state, "will_crit", "willCrit", "always_crit", "alwaysCrit"):
        return CRIT_GUARANTEED_STAGE

    stage = 0
    if move_id in _HIGH_CRIT_MOVES or _flag(move_state, "high_crit_ratio", "highCritRatio"):
        stage += 1

    explicit_bonus = _read_value(move_state, "crit_stage_bonus")
    if isinstance(explicit_bonus, int):
        stage += explicit_bonus
    crit_ratio = _read_value(move_state, "critRatio", "crit_ratio")
    if isinstance(crit_ratio, int):
        # Showdown move.critRatio is 2 for high-crit moves, i.e. +1 stage.
        stage += max(0, crit_ratio - 1)

    ability = _ability_id(attacker_state)
    if ability == "super-luck":
        stage += 1
    if ability == "merciless" and _status_id(defender_state) in {"poison", "poisoned", "toxic", "badly-poisoned"}:
        return CRIT_GUARANTEED_STAGE

    item = _item_id(attacker_state)
    if item in _STAGE_ONE_ITEMS:
        stage += 1
    if item == "stick" and _species_id(attacker_state) == "farfetchd":
        stage += 2
    if item == "lucky-punch" and _species_id(attacker_state) == "chansey":
        stage += 2

    volatiles = _volatiles(attacker_state)
    if "focus-energy" in volatiles:
        stage += 2
    if "lansat-berry" in volatiles or "lansat" in volatiles:
        stage += 2
    if "dragon-cheer" in volatiles:
        stage += 2 if "dragon" in _types(attacker_state) else 1

    return max(0, stage)


def crit_probability(stage: int) -> Fraction:
    """Return the exact Gen 9 critical-hit probability for a crit stage."""
    if stage <= 0:
        return Fraction(1, 24)
    if stage == 1:
        return Fraction(1, 8)
    if stage == 2:
        return Fraction(1, 2)
    return Fraction(1, 1)


def is_crit_blocked(defender_state: Any | None = None, field_state: Any | None = None) -> bool:
    """Return True when defender-side effects prevent critical hits."""
    if _ability_id(defender_state) in _CRIT_BLOCKING_ABILITIES:
        return True
    lucky_chant = _read_value(field_state, "lucky_chant", "defender_lucky_chant")
    if lucky_chant:
        return True
    defender_side = _read_value(field_state, "defender_side")
    if defender_side is not None and bool(_read_value(defender_side, "lucky_chant")):
        return True
    return False


def resolve_crit_roll(
    stage: int,
    mode: CritRollMode,
    rng: RNG | None = None,
    *,
    defender_state: Any | None = None,
    field_state: Any | None = None,
) -> bool | tuple[bool, bool] | dict[bool, int]:
    """Resolve a critical-hit outcome with the same five-mode contract as roll.py."""
    blocked = is_crit_blocked(defender_state, field_state)
    if mode == "min":
        return False
    if mode == "max":
        return not blocked
    if mode == "deterministic":
        return (False, not blocked)

    probability = Fraction(0, 1) if blocked else crit_probability(stage)
    if mode == "distribution":
        return {True: probability.numerator, False: probability.denominator - probability.numerator}
    if mode == "probabilistic":
        if probability == 0:
            return False
        if probability == 1:
            return True
        if rng is None:
            rng = RNG()
        return rng.random(probability.denominator) < probability.numerator
    raise ValueError(f"unsupported crit roll mode: {mode}")


def apply_crit_modifier(base_damage: int, is_crit: bool) -> int:
    """Apply the Gen 6+ critical-hit damage modifier."""
    if base_damage < 0:
        raise ValueError("base_damage must be non-negative")
    if not is_crit:
        return base_damage
    return (base_damage * 3) // 2


def resolve_crit_multiplier(
    is_crit: bool,
    attacker_ability: str | None = None,
) -> int:
    """Return the Q12 critical-hit multiplier, including Sniper."""
    if not is_crit:
        return Q12_ONE
    return apply_sniper(MUL_1_5, attacker_ability, is_crit)
