from __future__ import annotations

from advisor.damage.modifiers._q12 import MUL_0_5, MUL_0_75, MUL_2_0, MUL_2_25, q12_mul
from advisor.damage.q12 import Q12_ONE


_SE_REDUCERS = {"solidrock", "solid-rock", "filter", "prismarmor", "prism-armor"}


def normalize_id(value: str | None) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def apply_sniper(crit_mult_q12: int, attacker_ability: str | None, crit_landed: bool) -> int:
    """If Sniper and crit landed, return 2.25x in Q12; else passthrough."""
    if crit_landed and normalize_id(attacker_ability) == "sniper":
        return MUL_2_25
    return crit_mult_q12


def apply_adaptability(
    stab_mult_q12: int,
    attacker_ability: str | None,
    move_type: str,
    attacker_types: tuple[str, ...],
) -> int:
    """If Adaptability and STAB applies, return 2.0x; else passthrough."""
    types = tuple(normalize_id(t) for t in attacker_types)
    if normalize_id(attacker_ability) == "adaptability" and normalize_id(move_type) in types:
        return MUL_2_0
    return stab_mult_q12


def apply_tinted_lens(type_mult_q12: int, attacker_ability: str | None) -> int:
    """If Tinted Lens and type_mult < 1.0, double it."""
    if normalize_id(attacker_ability) == "tinted-lens" and type_mult_q12 < Q12_ONE:
        return q12_mul(type_mult_q12, MUL_2_0)
    return type_mult_q12


def apply_defender_se_resist(type_mult_q12: int, defender_ability: str | None) -> int:
    """Solid Rock / Filter / Prism Armor: if SE (>1.0), apply 0.75x."""
    if normalize_id(defender_ability) in _SE_REDUCERS and type_mult_q12 > Q12_ONE:
        return q12_mul(type_mult_q12, MUL_0_75)
    return type_mult_q12


def apply_multiscale(
    damage: int,
    defender_ability: str | None,
    defender_hp: int | None,
    defender_maxhp: int | None,
) -> int:
    """Multiscale / Shadow Shield: 0.5x damage if defender is at full HP."""
    if defender_hp is None or defender_maxhp is None or defender_maxhp <= 0:
        return damage
    if normalize_id(defender_ability) in {"multiscale", "shadow-shield"} and defender_hp == defender_maxhp:
        return (damage * MUL_0_5) // Q12_ONE
    return damage
