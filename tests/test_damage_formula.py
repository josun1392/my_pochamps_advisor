from __future__ import annotations

from advisor.damage.formula import DamageContext, base_damage, calc_damage_rolls
from advisor.damage.q12 import M_SPREAD, apply_damage_modifier
from advisor.damage.types import load_type_chart, type_effectiveness


def test_base_damage_known_neutral_case() -> None:
    assert base_damage(level=50, power=50, attack=100, defense=100) == 24


def test_neutral_damage_rolls_are_16_values() -> None:
    rolls = calc_damage_rolls(_ctx())

    assert len(rolls) == 16
    assert rolls == sorted(rolls)


def test_stab_increases_damage() -> None:
    no_stab = calc_damage_rolls(_ctx(attacker_types=("water",)))
    stab = calc_damage_rolls(_ctx(attacker_types=("fire",)))

    assert stab[0] > no_stab[0]


def test_type_immunity_returns_zero_rolls() -> None:
    rolls = calc_damage_rolls(
        _ctx(move_type="normal", attacker_types=("normal",), defender_types=("ghost",))
    )

    assert rolls == [0] * 16


def test_spread_modifier_applies_before_random() -> None:
    single = calc_damage_rolls(_ctx())
    spread = calc_damage_rolls(_ctx(is_spread=True))

    assert spread[0] < single[0]
    assert apply_damage_modifier(base_damage(50, 80, 120, 100), M_SPREAD) == 33


def test_critical_hit_increases_damage() -> None:
    normal = calc_damage_rolls(_ctx())
    crit = calc_damage_rolls(_ctx(is_critical=True))

    assert crit[0] > normal[0]


def test_type_effectiveness_q12_values() -> None:
    chart = load_type_chart()

    assert type_effectiveness("ice", ("dragon", "ground"), chart) == 16384
    assert type_effectiveness("normal", ("ghost",), chart) == 0


def _ctx(
    *,
    move_type: str = "fire",
    attacker_types: tuple[str, ...] = ("fire",),
    defender_types: tuple[str, ...] = ("electric",),
    is_spread: bool = False,
    is_critical: bool = False,
) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=80,
        attack_stat=120,
        defense_stat=100,
        move_type=move_type,
        attacker_types=attacker_types,
        defender_types=defender_types,
        is_physical=False,
        is_critical=is_critical,
        is_spread=is_spread,
    )
