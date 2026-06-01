from __future__ import annotations

import time
from statistics import median

from advisor.damage.formula import DamageContext, calc_damage_rolls
from advisor.damage.field import Field, SideField
from advisor.damage.grounded import GroundedInputs
from advisor.damage.abilities import get_ability
from advisor.damage.items import get_item
from advisor.damage.stats import StatBlock


PERF_ITERATIONS = 1000
PERF_REPEATS = 5
PERF_WARMUP_ITERATIONS = 100


def _assert_damage_calc_median_under(
    ctx: DamageContext,
    *,
    threshold_ms: float,
    test_name: str,
    iterations: int = PERF_ITERATIONS,
    repeats: int = PERF_REPEATS,
    warmup_iterations: int = PERF_WARMUP_ITERATIONS,
) -> tuple[float, list[float]]:
    for _ in range(warmup_iterations):
        calc_damage_rolls(ctx)

    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(iterations):
            calc_damage_rolls(ctx)
        samples.append((time.perf_counter() - start) * 1000 / iterations)

    median_ms = median(samples)
    assert median_ms < threshold_ms, (
        f"median average {median_ms:.6f}ms exceeded threshold {threshold_ms:.6f}ms; "
        f"samples={[round(sample, 6) for sample in samples]}, "
        f"min={min(samples):.6f}ms, max={max(samples):.6f}ms. "
        f"Isolated rerun command: uv run pytest tests/test_damage_perf.py::{test_name} -q. "
        "If this fails only under the full suite, rerun isolated 3 times before changing threshold."
    )
    return median_ms, samples


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

    _assert_damage_calc_median_under(
        ctx,
        threshold_ms=5.0,
        test_name="test_damage_calculation_under_5ms_average",
    )


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

    _assert_damage_calc_median_under(
        ctx,
        threshold_ms=6.0,
        test_name="test_field_damage_calculation_under_6ms_average",
    )


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

    _assert_damage_calc_median_under(
        ctx,
        threshold_ms=0.12,
        test_name="test_item_damage_calculation_under_point_12ms_average",
    )


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

    _assert_damage_calc_median_under(
        ctx,
        threshold_ms=0.20,
        test_name="test_ability_damage_calculation_under_point_20ms_average",
    )
