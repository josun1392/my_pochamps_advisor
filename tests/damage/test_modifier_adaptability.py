from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext
from advisor.damage.modifiers.abilities import apply_adaptability
from advisor.damage.modifiers._q12 import MUL_2_0
from advisor.damage.q12 import M_STAB, Q12_ONE, apply_damage_modifier


def _ctx(*, ability: str | None, types: tuple[str, ...] = ("dark",)) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=65,
        attack_stat=120,
        defense_stat=100,
        move_type="dark",
        move_id="knock-off",
        attacker_types=types,
        defender_types=("electric",),
        is_physical=True,
        is_critical=False,
        is_spread=False,
        field=Field(),
        attacker_ability=get_ability(ability),
    )


def test_apply_adaptability_stab_returns_2x() -> None:
    assert apply_adaptability(M_STAB, "adaptability", "dark", ("water", "dark")) == MUL_2_0


def test_apply_adaptability_no_stab_passthrough() -> None:
    assert apply_adaptability(Q12_ONE, "adaptability", "dark", ("water",)) == Q12_ONE


def test_apply_adaptability_absent_passthrough() -> None:
    assert apply_adaptability(M_STAB, None, "dark", ("dark",)) == M_STAB


def test_calculator_adaptability_stab_is_2x() -> None:
    no_stab = calculate(_ctx(ability=None, types=("water",)))
    adaptability = calculate(_ctx(ability="adaptability"))

    assert isinstance(no_stab, int)
    assert adaptability == apply_damage_modifier(no_stab, MUL_2_0)
