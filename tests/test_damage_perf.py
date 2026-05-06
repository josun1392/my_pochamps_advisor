from __future__ import annotations

import time

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.field import Field, SideField
from advisor.damage.grounded import GroundedInputs
from advisor.damage.abilities import get_ability
from advisor.damage.items import get_item
from advisor.damage.stats import StatBlock


def test_damage_calculation_under_5ms_average() -> None:
    ctx = DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=150,
        defense_stat=120,
        move_type="fire",
        attacker_types=("fire", "flying"),
        defender_types=("grass", "poison"),
        is_physical=False,
        is_critical=False,
        is_spread=False,
    )
    iterations = 1000

    start = time.perf_counter()
    for _ in range(iterations):
        calc_damage_rolls(ctx)
    elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

    assert elapsed_ms < 5.0


def test_field_damage_calculation_under_6ms_average() -> None:
    ctx = DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=150,
        defense_stat=120,
        move_type="fire",
        move_id="flamethrower",
        attacker_types=("fire", "flying"),
        defender_types=("grass", "poison"),
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(weather="sun", terrain="grassy", defender_side=SideField(light_screen=True)),
        attacker_grounded_inputs=GroundedInputs(("fire", "flying")),
        defender_grounded_inputs=GroundedInputs(("grass", "poison")),
    )
    iterations = 1000

    start = time.perf_counter()
    for _ in range(iterations):
        calc_damage_rolls(ctx)
    elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

    assert elapsed_ms < 6.0


def test_item_damage_calculation_under_point_12ms_average() -> None:
    ctx = DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=150,
        defense_stat=120,
        move_type="fire",
        move_id="flamethrower",
        attacker_types=("fire", "flying"),
        defender_types=("grass", "poison"),
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(weather="sun", defender_side=SideField(light_screen=True)),
        attacker_grounded_inputs=GroundedInputs(("fire", "flying")),
        defender_grounded_inputs=GroundedInputs(("grass", "poison")),
        attacker_item=get_item("life-orb"),
        defender_item=get_item("occa-berry"),
        attacker_species="charizard",
        defender_species="venusaur",
    )
    iterations = 1000

    start = time.perf_counter()
    for _ in range(iterations):
        calc_damage_rolls(ctx)
    elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

    assert elapsed_ms < 0.12


def test_ability_damage_calculation_under_point_20ms_average() -> None:
    stats = StatBlock(hp=78, atk=84, def_=78, spa=109, spd=85, spe=100)
    ctx = DamageContext(
        attacker_level=50,
        move_power=90,
        attack_stat=150,
        defense_stat=120,
        move_type="fire",
        move_id="flamethrower",
        attacker_types=("fire", "flying"),
        defender_types=("grass", "poison"),
        is_physical=False,
        is_critical=False,
        is_spread=False,
        field=Field(weather="sun", defender_side=SideField(light_screen=True)),
        attacker_grounded_inputs=GroundedInputs(("fire", "flying")),
        defender_grounded_inputs=GroundedInputs(("grass", "poison")),
        attacker_item=get_item("life-orb"),
        defender_item=get_item("occa-berry"),
        attacker_species="charizard",
        defender_species="venusaur",
        attacker_ability=get_ability("solar-power"),
        attacker_stats=stats,
    )
    iterations = 1000

    start = time.perf_counter()
    for _ in range(iterations):
        calc_damage_rolls(ctx)
    elapsed_ms = (time.perf_counter() - start) * 1000 / iterations

    assert elapsed_ms < 0.20
