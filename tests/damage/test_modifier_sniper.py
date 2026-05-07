from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext
from advisor.damage.modifiers.abilities import apply_sniper
from advisor.damage.modifiers._q12 import MUL_1_5, MUL_2_25


def _ctx(ability: str | None = None) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=70,
        attack_stat=120,
        defense_stat=100,
        move_type="dark",
        move_id="night-slash",
        attacker_types=("dark",),
        defender_types=("electric",),
        is_physical=True,
        is_critical=False,
        is_spread=False,
        field=Field(),
        attacker_ability=get_ability(ability),
    )


def test_apply_sniper_crit_landed_returns_2_25() -> None:
    assert apply_sniper(MUL_1_5, "sniper", True) == MUL_2_25


def test_apply_sniper_no_crit_passthrough() -> None:
    assert apply_sniper(MUL_1_5, "sniper", False) == MUL_1_5


def test_apply_sniper_absent_passthrough() -> None:
    assert apply_sniper(MUL_1_5, None, True) == MUL_1_5


def test_calculator_sniper_crit_exceeds_normal_crit() -> None:
    normal = calculate(_ctx(), crit_mode="max")
    sniper = calculate(_ctx("sniper"), crit_mode="max")

    assert isinstance(normal, int)
    assert isinstance(sniper, int)
    assert sniper > normal
