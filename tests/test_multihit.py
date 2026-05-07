from __future__ import annotations

from fractions import Fraction

import pytest

from advisor.damage.multihit import MULTIHIT_MOVES
from advisor.probability import compute_ko_probability_with_effects
from advisor.probability.multi_hit import (
    compute_multihit_damage_distribution,
    compute_multihit_distribution,
    repeated_hit_distribution,
)
from advisor.probability.residual import ResidualSpec


BULLET_SEED = MULTIHIT_MOVES["bullet-seed"]
ROCK_BLAST = MULTIHIT_MOVES["rock-blast"]
TAIL_SLAP = MULTIHIT_MOVES["tail-slap"]
PIN_MISSILE = MULTIHIT_MOVES["pin-missile"]
WATER_SHURIKEN = MULTIHIT_MOVES["water-shuriken"]
POPULATION_BOMB = MULTIHIT_MOVES["population-bomb"]
TRIPLE_AXEL = MULTIHIT_MOVES["triple-axel"]


def test_bullet_seed_default_hit_count_distribution() -> None:
    assert compute_multihit_distribution(BULLET_SEED, {}) == {
        2: Fraction(35, 100),
        3: Fraction(35, 100),
        4: Fraction(15, 100),
        5: Fraction(15, 100),
    }


@pytest.mark.parametrize("move", [BULLET_SEED, ROCK_BLAST, TAIL_SLAP, PIN_MISSILE, WATER_SHURIKEN])
def test_skill_link_forces_five_hits_for_range_moves(move) -> None:
    assert compute_multihit_distribution(move, {"ability": "skill-link"}) == {5: Fraction(1, 1)}


@pytest.mark.parametrize("move", [BULLET_SEED, ROCK_BLAST, TAIL_SLAP, PIN_MISSILE, WATER_SHURIKEN])
def test_loaded_dice_forces_four_or_five_for_range_moves(move) -> None:
    assert compute_multihit_distribution(move, {"item": "loaded-dice"}) == {
        4: Fraction(1, 2),
        5: Fraction(1, 2),
    }


def test_skill_link_beats_loaded_dice_for_range_moves() -> None:
    assert compute_multihit_distribution(BULLET_SEED, {"ability": "skill-link", "item": "loaded-dice"}) == {
        5: Fraction(1, 1),
    }


def test_population_bomb_default_distribution_has_one_to_ten_hits() -> None:
    distribution = compute_multihit_distribution(POPULATION_BOMB, {})

    assert set(distribution) == set(range(1, 11))
    assert sum(distribution.values(), Fraction(0, 1)) == 1


def test_population_bomb_skill_link_forces_ten_hits() -> None:
    assert compute_multihit_distribution(POPULATION_BOMB, {"ability": "skill-link"}) == {10: Fraction(1, 1)}


def test_population_bomb_loaded_dice_is_uniform_four_to_ten() -> None:
    assert compute_multihit_distribution(POPULATION_BOMB, {"item": "loaded-dice"}) == {
        hits: Fraction(1, 7) for hits in range(4, 11)
    }


def test_population_bomb_loaded_dice_still_applies_with_skill_link() -> None:
    assert compute_multihit_distribution(POPULATION_BOMB, {"ability": "skill-link", "item": "loaded-dice"}) == {
        hits: Fraction(1, 7) for hits in range(4, 11)
    }


def test_repeated_hit_distribution_two_hits_convolves_independently() -> None:
    result = repeated_hit_distribution({10: Fraction(1, 2), 20: Fraction(1, 2)}, 2)

    assert result == {20: Fraction(1, 4), 30: Fraction(1, 2), 40: Fraction(1, 4)}


def test_compute_multihit_damage_distribution_weights_hit_counts() -> None:
    result = compute_multihit_damage_distribution(
        {10: Fraction(1, 1)},
        {2: Fraction(1, 4), 3: Fraction(3, 4)},
    )

    assert result == {20: Fraction(1, 4), 30: Fraction(3, 4)}


def test_compute_ko_probability_with_multihit_uses_one_move_distribution() -> None:
    result = compute_ko_probability_with_effects(100, 201, move=BULLET_SEED, attacker={}, crit_rate=Fraction(0, 1), max_turns=1)

    assert result.ohko == Fraction(65, 100)


def test_compute_ko_probability_with_skill_link_multihit_is_guaranteed() -> None:
    result = compute_ko_probability_with_effects(
        100,
        401,
        move=BULLET_SEED,
        attacker={"ability": "skill-link"},
        crit_rate=Fraction(0, 1),
        max_turns=1,
    )

    assert result.ohko == 1


def test_compute_ko_probability_with_loaded_dice_beats_high_threshold() -> None:
    result = compute_ko_probability_with_effects(
        100,
        301,
        move=BULLET_SEED,
        attacker={"item": "loaded-dice"},
        crit_rate=Fraction(0, 1),
        max_turns=1,
    )

    assert result.ohko == 1


def test_multihit_plus_burn_chip_can_turn_miss_into_ko() -> None:
    no_chip = compute_ko_probability_with_effects(100, 205, move=BULLET_SEED, attacker={}, crit_rate=Fraction(0, 1), max_turns=1)
    with_chip = compute_ko_probability_with_effects(
        100,
        205,
        move=BULLET_SEED,
        attacker={},
        residuals=ResidualSpec("burn", max_hp=80),
        crit_rate=Fraction(0, 1),
        max_turns=1,
    )

    assert with_chip.ohko > no_chip.ohko


def test_multihit_with_sniper_crit_damage_contributes_to_ko() -> None:
    result = compute_ko_probability_with_effects(
        100,
        501,
        move=BULLET_SEED,
        attacker={"ability": "skill-link"},
        crit_rate=Fraction(1, 8),
        crit_damage_q12=225,
        max_turns=1,
    )

    assert result.ohko == Fraction(1, 8)
    assert result.crit_contribution == Fraction(1, 8)


def test_compute_ko_probability_with_effects_preserves_four_turn_monotonicity() -> None:
    result = compute_ko_probability_with_effects(100, 700, move=BULLET_SEED, attacker={}, crit_rate=Fraction(0, 1), max_turns=4)

    assert result.by_turn[1] <= result.by_turn[2] <= result.by_turn[3] <= result.by_turn[4]
