from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext
from advisor.damage.modifiers.abilities import apply_tinted_lens
from advisor.damage.q12 import Q12_ONE


def _ctx(ability: str | None = None, defender_types: tuple[str, ...] = ("grass",)) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=120,
        defense_stat=100,
        move_type="water",
        move_id="water-gun",
        attacker_types=("water",),
        defender_types=defender_types,
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(),
        attacker_ability=get_ability(ability),
    )


def test_apply_tinted_lens_doubles_resisted_q12() -> None:
    assert apply_tinted_lens(2048, "tinted-lens") == Q12_ONE


def test_apply_tinted_lens_quad_resist_becomes_half() -> None:
    assert apply_tinted_lens(1024, "tinted-lens") == 2048


def test_apply_tinted_lens_neutral_passthrough() -> None:
    assert apply_tinted_lens(Q12_ONE, "tinted-lens") == Q12_ONE


def test_apply_tinted_lens_absent_passthrough() -> None:
    assert apply_tinted_lens(2048, None) == 2048


def test_calculator_tinted_lens_lifts_half_to_neutral() -> None:
    resisted = calculate(_ctx())
    tinted = calculate(_ctx("tinted-lens"))

    assert isinstance(resisted, int)
    assert tinted == resisted * 2 or tinted == resisted + resisted
