from __future__ import annotations

from fractions import Fraction
from typing import Final


Q12_ONE: Final[int] = 4096

M_NEUTRAL: Final[int] = 4096
M_HALF: Final[int] = 2048
M_SPREAD: Final[int] = 3072
M_STAB: Final[int] = 6144
M_DOUBLE: Final[int] = 8192
M_STAB_ADAPTABILITY: Final[int] = 8192
M_WEATHER_BOOST: Final[int] = 6144
M_WEATHER_NERF: Final[int] = 2048
M_TERRAIN_BOOST: Final[int] = 5325
M_TERRAIN_NERF: Final[int] = 2048
M_SCREEN_SINGLES: Final[int] = 2048
M_SCREEN_DOUBLES: Final[int] = 2732
M_SAND_SPDEF: Final[int] = 6144
M_SNOW_DEF: Final[int] = 6144
M_TERA_STAB: Final[int] = 6144
M_TERA_DOUBLE_STAB: Final[int] = 8192


def to_q12(rational: float) -> int:
    """Convert a debug float to Q12. Prefer named integer constants in code."""
    return round(rational * Q12_ONE)


def pokeround(value: int | float | Fraction) -> int:
    """Pokemon-style rounding: fractions exactly at .5 round down."""
    fraction = Fraction(value)
    quotient = fraction.numerator // fraction.denominator
    remainder = fraction.numerator % fraction.denominator
    return quotient + int(remainder * 2 > fraction.denominator)


def apply_modifier(value: int, modifier_q12: int) -> int:
    """Apply a single Q12 modifier using the modifier-chain rounding rule."""
    return (value * modifier_q12 + 2048) >> 12


def apply_damage_modifier(value: int, modifier_q12: int) -> int:
    """Apply a Q12 modifier where the Gen 9 damage path uses pokeround."""
    product = value * modifier_q12
    quotient = product // Q12_ONE
    remainder = product % Q12_ONE
    return quotient + int(remainder * 2 > Q12_ONE)


def chain_modifiers(modifiers: list[int]) -> int:
    """Chain Q12 modifiers, rounding after each multiplication."""
    result = Q12_ONE
    for modifier in modifiers:
        if modifier != Q12_ONE:
            result = (result * modifier + 2048) >> 12
    return result
