from __future__ import annotations

from fractions import Fraction

from advisor.damage.q12 import (
    M_DOUBLE,
    M_HALF,
    M_NEUTRAL,
    M_STAB,
    Q12_ONE,
    apply_damage_modifier,
    apply_modifier,
    chain_modifiers,
    pokeround,
    to_q12,
)


def test_to_q12() -> None:
    assert to_q12(1.5) == M_STAB


def test_apply_modifier_stab() -> None:
    assert apply_modifier(100, M_STAB) == 150


def test_apply_modifier_half() -> None:
    assert apply_modifier(100, M_HALF) == 50


def test_apply_damage_modifier_half_down() -> None:
    assert apply_damage_modifier(1, M_STAB) == 1


def test_chain_modifiers_stab_double() -> None:
    assert chain_modifiers([M_STAB, M_DOUBLE]) == 12288


def test_chain_modifiers_stab_half() -> None:
    assert chain_modifiers([M_STAB, M_HALF]) == 3072


def test_chain_modifiers_empty() -> None:
    assert chain_modifiers([]) == Q12_ONE


def test_chain_modifiers_skips_neutral() -> None:
    assert chain_modifiers([M_NEUTRAL, M_STAB, M_NEUTRAL]) == M_STAB


def test_known_life_orb_chain_case() -> None:
    chained = chain_modifiers([6144, 5325, 4096])

    assert chained == 7988
    assert apply_modifier(100, chained) == 195


def test_pokeround_half_down() -> None:
    assert pokeround(Fraction(3, 2)) == 1
    assert pokeround(Fraction(31, 20)) == 2
