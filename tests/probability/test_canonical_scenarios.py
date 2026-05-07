from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from advisor.damage.abilities import get_ability
from advisor.damage.calculator import calculate
from advisor.damage.field import Field
from advisor.damage.formula import DamageContext
from advisor.damage.items import get_item
from advisor.probability import compute_ko_probability
from advisor.probability.rolls import roll_outcomes


def _ctx(
    *,
    move_type: str,
    move_id: str,
    attacker_types: tuple[str, ...],
    defender_types: tuple[str, ...],
    move_power: int = 90,
    attack: int = 150,
    defense: int = 100,
    physical: bool = True,
    attacker_ability: str | None = None,
    defender_ability: str | None = None,
    attacker_item: str | None = None,
    weather: str = "none",
    defender_hp_ratio: float = 1.0,
) -> DamageContext:
    return DamageContext(
        attacker_level=50,
        move_power=move_power,
        attack_stat=attack,
        defense_stat=defense,
        move_type=move_type,
        move_id=move_id,
        attacker_types=attacker_types,
        defender_types=defender_types,
        is_physical=physical,
        is_critical=False,
        is_spread=False,
        field=Field(weather=weather),  # type: ignore[arg-type]
        attacker_ability=get_ability(attacker_ability),
        defender_ability=get_ability(defender_ability),
        attacker_item=get_item(attacker_item),
        defender_hp_current=100 if defender_hp_ratio == 1.0 else 99,
        defender_hp_max=100,
        defender_hp_ratio=defender_hp_ratio,
    )


def _max_damage(ctx: DamageContext) -> int:
    result = calculate(ctx)
    assert isinstance(result, int)
    return result


def test_garchomp_earthquake_tyranitar_guaranteed_2hko() -> None:
    damage = _max_damage(_ctx(move_type="ground", move_id="earthquake", attacker_types=("dragon", "ground"), defender_types=("rock", "dark")))
    target_hp = roll_outcomes(damage)[0] * 2
    result = compute_ko_probability(damage, target_hp)

    assert result.by_turn[1] < 1
    assert result.by_turn[2] == 1


def test_iron_moth_fiery_dance_tinted_lens_ohko_probability() -> None:
    normal = _ctx(move_type="fire", move_id="fiery-dance", attacker_types=("fire", "poison"), defender_types=("water",), physical=False)
    tinted = replace(normal, attacker_ability=get_ability("tinted-lens"))

    assert compute_ko_probability(_max_damage(tinted), _max_damage(normal) + 1).ohko > 0


def test_drapion_sniper_crit_knock_off_ohko_distribution() -> None:
    normal = _ctx(move_type="dark", move_id="knock-off", attacker_types=("dark", "poison"), defender_types=("electric",), attacker_ability="sniper")
    crit_damage = calculate(normal, crit_mode="max")
    assert isinstance(crit_damage, int)
    target_hp = _max_damage(normal) + 1
    normal_only = compute_ko_probability(_max_damage(normal), target_hp, crit_rate=Fraction(0, 1))
    result = compute_ko_probability(_max_damage(normal), target_hp, crit_rate=Fraction(1, 8), crit_damage_q12=crit_damage)

    assert result.ohko > normal_only.ohko
    assert result.crit_contribution > 0


def test_multiscale_dragonite_full_hp_changes_2hko_curve() -> None:
    base = _ctx(move_type="ice", move_id="ice-beam", attacker_types=("ice",), defender_types=("dragon", "flying"), physical=False)
    scaled = replace(base, defender_ability=get_ability("multiscale"))

    assert compute_ko_probability(_max_damage(scaled), _max_damage(base)).ohko < compute_ko_probability(_max_damage(base), _max_damage(base)).ohko


def test_choice_specs_pelipper_hurricane_neutral_ohko() -> None:
    ctx = _ctx(move_type="flying", move_id="hurricane", attacker_types=("water", "flying"), defender_types=("electric",), physical=False, attacker_item="choice-specs")

    assert compute_ko_probability(_max_damage(ctx), _max_damage(ctx)).ohko == Fraction(1, 16)


def test_adaptability_dragapult_shadow_ball_increases_stab_damage() -> None:
    base = _ctx(move_type="ghost", move_id="shadow-ball", attacker_types=("dragon", "ghost"), defender_types=("electric",), physical=False)
    adaptability = replace(base, attacker_ability=get_ability("adaptability"))

    assert _max_damage(adaptability) > _max_damage(base)


def test_solid_rock_rhyperior_se_reflected_in_probability() -> None:
    base = _ctx(move_type="water", move_id="surf", attacker_types=("water",), defender_types=("rock", "ground"), physical=False)
    solid_rock = replace(base, defender_ability=get_ability("solid-rock"))

    assert compute_ko_probability(_max_damage(solid_rock), _max_damage(base)).ohko < 1


def test_sand_rush_excadrill_eq_in_sand_speed_irrelevant() -> None:
    base = _ctx(move_type="ground", move_id="earthquake", attacker_types=("ground", "steel"), defender_types=("electric",), attacker_ability="sand-rush", weather="sand")
    no_ability = replace(base, attacker_ability=None)

    assert compute_ko_probability(_max_damage(base), _max_damage(no_ability)).ohko == compute_ko_probability(_max_damage(no_ability), _max_damage(no_ability)).ohko


def test_life_orb_garchomp_outrage_recoil_scope_out() -> None:
    base = _ctx(move_type="dragon", move_id="outrage", attacker_types=("dragon", "ground"), defender_types=("electric",), attacker_item=None)
    life_orb = replace(base, attacker_item=get_item("life-orb"))

    assert _max_damage(life_orb) > _max_damage(base)


def test_boots_heatran_baseline_ohko_probability() -> None:
    ctx = _ctx(move_type="fire", move_id="flamethrower", attacker_types=("fire", "steel"), defender_types=("electric",), physical=False, attacker_item="heavy-duty-boots")

    assert compute_ko_probability(_max_damage(ctx), _max_damage(ctx)).ohko == Fraction(1, 16)
