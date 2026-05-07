from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext
from advisor.damage.modifiers.abilities import apply_multiscale


def _ctx(
    ability: str | None,
    *,
    hp_current: int | None = 100,
    hp_max: int | None = 100,
    hp_ratio: float = 1.0,
) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=120,
        defense_stat=100,
        move_type="ice",
        move_id="ice-beam",
        attacker_types=("ice",),
        defender_types=("dragon", "flying"),
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(),
        defender_ability=get_ability(ability),
        defender_hp_current=hp_current,
        defender_hp_max=hp_max,
        defender_hp_ratio=hp_ratio,
    )


def test_apply_multiscale_full_hp_halves_damage() -> None:
    assert apply_multiscale(101, "multiscale", 100, 100) == 50


def test_apply_shadow_shield_full_hp_halves_damage() -> None:
    assert apply_multiscale(100, "shadow-shield", 1, 1) == 50


def test_apply_multiscale_not_full_passthrough() -> None:
    assert apply_multiscale(100, "multiscale", 99, 100) == 100


def test_apply_multiscale_absent_passthrough() -> None:
    assert apply_multiscale(100, None, 100, 100) == 100


def test_apply_multiscale_missing_hp_passthrough() -> None:
    assert apply_multiscale(100, "multiscale", None, None) == 100


def test_calculator_multiscale_full_hp_halves_after_final_mods() -> None:
    normal = calculate(_ctx(None))
    multiscale = calculate(_ctx("multiscale"))

    assert isinstance(normal, int)
    assert multiscale == normal // 2


def test_calculator_multiscale_99_percent_no_effect() -> None:
    normal = calculate(_ctx(None, hp_current=99, hp_max=100, hp_ratio=0.99))
    multiscale = calculate(_ctx("multiscale", hp_current=99, hp_max=100, hp_ratio=0.99))

    assert multiscale == normal
