from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext
from advisor.damage.modifiers.abilities import apply_defender_se_resist
from advisor.damage.modifiers._q12 import MUL_0_75
from advisor.damage.q12 import Q12_ONE, apply_damage_modifier


def _ctx(ability: str | None = None, defender_types: tuple[str, ...] = ("rock",)) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=100,
        attack_stat=120,
        defense_stat=100,
        move_type="ground",
        move_id="earthquake",
        attacker_types=("ground",),
        defender_types=defender_types,
        is_physical=True,
        is_critical=False,
        is_spread=False,
        field=Field(),
        defender_ability=get_ability(ability),
    )


def test_apply_solid_rock_q12_on_super_effective() -> None:
    assert apply_defender_se_resist(8192, "solid-rock") == 6144


def test_apply_filter_q12_on_super_effective() -> None:
    assert apply_defender_se_resist(8192, "filter") == 6144


def test_apply_prism_armor_q12_on_super_effective() -> None:
    assert apply_defender_se_resist(8192, "prism-armor") == 6144


def test_apply_defender_se_resist_neutral_passthrough() -> None:
    assert apply_defender_se_resist(Q12_ONE, "solid-rock") == Q12_ONE


def test_apply_defender_se_resist_absent_passthrough() -> None:
    assert apply_defender_se_resist(8192, None) == 8192


def test_calculator_solid_rock_reduces_super_effective_damage() -> None:
    normal = calculate(_ctx())
    solid_rock = calculate(_ctx("solid-rock"))

    assert isinstance(normal, int)
    assert solid_rock == apply_damage_modifier(normal, MUL_0_75)
