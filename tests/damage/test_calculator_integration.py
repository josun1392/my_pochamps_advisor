from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext


def _ctx(
    *,
    move_type: str,
    move_id: str,
    attacker_types: tuple[str, ...],
    defender_types: tuple[str, ...],
    attacker_ability: str | None = None,
    defender_ability: str | None = None,
    defender_hp_current: int | None = None,
    defender_hp_max: int | None = None,
    move_power: int = 80,
) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=move_power,
        attack_stat=140,
        defense_stat=100,
        move_type=move_type,
        move_id=move_id,
        attacker_types=attacker_types,
        defender_types=defender_types,
        is_physical=True,
        is_critical=False,
        is_spread=False,
        field=Field(),
        attacker_ability=get_ability(attacker_ability),
        defender_ability=get_ability(defender_ability),
        defender_hp_current=defender_hp_current,
        defender_hp_max=defender_hp_max,
        defender_hp_ratio=1.0 if defender_hp_current == defender_hp_max else 0.99,
    )


def test_drapion_sniper_night_slash_crit_is_stronger_than_normal_crit() -> None:
    normal_crit = calculate(
        _ctx(move_type="dark", move_id="night-slash", attacker_types=("dark", "poison"), defender_types=("electric",)),
        crit_mode="max",
    )
    sniper_crit = calculate(
        _ctx(
            move_type="dark",
            move_id="night-slash",
            attacker_types=("dark", "poison"),
            defender_types=("electric",),
            attacker_ability="sniper",
        ),
        crit_mode="max",
    )

    assert sniper_crit > normal_crit


def test_crawdaunt_adaptability_knock_off_stab_boost() -> None:
    regular = calculate(_ctx(move_type="dark", move_id="knock-off", attacker_types=("dark", "water"), defender_types=("electric",)))
    adaptability = calculate(
        _ctx(
            move_type="dark",
            move_id="knock-off",
            attacker_types=("dark", "water"),
            defender_types=("electric",),
            attacker_ability="adaptability",
        )
    )

    assert adaptability > regular


def test_iron_moth_tinted_lens_sludge_wave_vs_steel_lifts_resist() -> None:
    resisted = calculate(_ctx(move_type="poison", move_id="sludge-wave", attacker_types=("fire", "poison"), defender_types=("steel",)))
    tinted = calculate(
        _ctx(
            move_type="poison",
            move_id="sludge-wave",
            attacker_types=("fire", "poison"),
            defender_types=("steel",),
            attacker_ability="tinted-lens",
        )
    )

    assert tinted == resisted * 2


def test_aggron_solid_rock_earthquake_4x_reduced() -> None:
    normal = calculate(_ctx(move_type="ground", move_id="earthquake", attacker_types=("ground",), defender_types=("rock", "steel")))
    solid_rock = calculate(
        _ctx(
            move_type="ground",
            move_id="earthquake",
            attacker_types=("ground",),
            defender_types=("rock", "steel"),
            defender_ability="solid-rock",
        )
    )

    assert solid_rock < normal


def test_dragonite_multiscale_full_hp_halves_ice_beam() -> None:
    normal = calculate(_ctx(move_type="ice", move_id="ice-beam", attacker_types=("ice",), defender_types=("dragon", "flying")))
    multiscale = calculate(
        _ctx(
            move_type="ice",
            move_id="ice-beam",
            attacker_types=("ice",),
            defender_types=("dragon", "flying"),
            defender_ability="multiscale",
            defender_hp_current=100,
            defender_hp_max=100,
        )
    )

    assert multiscale == normal // 2


def test_dragonite_multiscale_99_percent_no_effect() -> None:
    normal = calculate(
        _ctx(move_type="ice", move_id="ice-beam", attacker_types=("ice",), defender_types=("dragon", "flying"), defender_hp_current=99, defender_hp_max=100)
    )
    multiscale = calculate(
        _ctx(
            move_type="ice",
            move_id="ice-beam",
            attacker_types=("ice",),
            defender_types=("dragon", "flying"),
            defender_ability="multiscale",
            defender_hp_current=99,
            defender_hp_max=100,
        )
    )

    assert multiscale == normal


def test_negative_no_modifier_matches_golden_value() -> None:
    assert calculate(_ctx(move_type="normal", move_id="tackle", attacker_types=("normal",), defender_types=("electric",))) == 76
