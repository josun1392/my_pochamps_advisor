from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.type_immunity import (
    is_immune_by_ability,
    is_wonder_guard_blocked,
    move_flags_for,
)


def test_volt_absorb_blocks_electric() -> None:
    assert is_immune_by_ability(
        "electric",
        "thunderbolt",
        (),
        get_ability("volt-absorb"),
        defender_grounded=True,
        mold_breaker_active=False,
    )


def test_mold_breaker_bypasses_volt_absorb() -> None:
    assert not is_immune_by_ability(
        "electric",
        "thunderbolt",
        (),
        get_ability("volt-absorb"),
        defender_grounded=True,
        mold_breaker_active=True,
    )


def test_levitate_requires_not_grounded() -> None:
    assert is_immune_by_ability(
        "ground",
        "earthquake",
        (),
        get_ability("levitate"),
        defender_grounded=False,
        mold_breaker_active=False,
    )
    assert not is_immune_by_ability(
        "ground",
        "earthquake",
        (),
        get_ability("levitate"),
        defender_grounded=True,
        mold_breaker_active=False,
    )


def test_move_flag_immunities() -> None:
    assert "bullet" in move_flags_for("shadow-ball")
    assert is_immune_by_ability(
        "ghost",
        "shadow-ball",
        move_flags_for("shadow-ball"),
        get_ability("bulletproof"),
        defender_grounded=True,
        mold_breaker_active=False,
    )
    assert is_immune_by_ability(
        "normal",
        "boomburst",
        move_flags_for("boomburst"),
        get_ability("soundproof"),
        defender_grounded=True,
        mold_breaker_active=False,
    )
    assert is_immune_by_ability(
        "grass",
        "spore",
        move_flags_for("spore"),
        get_ability("overcoat"),
        defender_grounded=True,
        mold_breaker_active=False,
    )


def test_wonder_guard_blocks_non_super_effective_only() -> None:
    wonder_guard = get_ability("wonder-guard")
    assert is_wonder_guard_blocked(1.0, wonder_guard, mold_breaker_active=False)
    assert is_wonder_guard_blocked(0.5, wonder_guard, mold_breaker_active=False)
    assert not is_wonder_guard_blocked(2.0, wonder_guard, mold_breaker_active=False)
    assert not is_wonder_guard_blocked(1.0, wonder_guard, mold_breaker_active=True)
