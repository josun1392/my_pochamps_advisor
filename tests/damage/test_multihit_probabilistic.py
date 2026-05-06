from __future__ import annotations

import pytest

from advisor.damage.multihit import MultiHitAttacker, MultiHitMove, resolve_hit_count
from advisor.damage.rng import RNG


N = 10_000
TOL = 0.05

BULLET_SEED = MultiHitMove("bullet-seed")
POPULATION_BOMB = MultiHitMove("population-bomb")
NO_ITEM_NO_ABILITY = MultiHitAttacker()
WITH_LOADED_DICE = MultiHitAttacker(item="loaded-dice")
WITH_SKILL_LINK = MultiHitAttacker(ability="skill-link")
SKILL_LINK_LOADED_DICE = MultiHitAttacker(ability="skill-link", item="loaded-dice")


def _mean(move: MultiHitMove, attacker: MultiHitAttacker, seed: int = 42) -> float:
    rng = RNG(seed)
    return sum(
        resolve_hit_count(move, attacker, mode="probabilistic", rng=rng)
        for _ in range(N)
    ) / N


def test_rng_random_matches_showdown_integer_shape() -> None:
    rng = RNG(12345)

    assert [rng.random(4) for _ in range(5)] == [3, 0, 2, 2, 1]


def test_rng_weighted_choice_is_seedable() -> None:
    rng = RNG(12345)

    assert [rng.weighted_choice([35, 35, 15, 15]) for _ in range(5)] == [1, 3, 0, 1, 1]


def test_probabilistic_mode_without_rng_uses_system_seed() -> None:
    assert 2 <= resolve_hit_count(BULLET_SEED, NO_ITEM_NO_ABILITY, mode="probabilistic") <= 5


def test_deterministic_mode_returns_min_max_tuple() -> None:
    assert resolve_hit_count(BULLET_SEED, NO_ITEM_NO_ABILITY, mode="deterministic") == (2, 5)
    assert resolve_hit_count(POPULATION_BOMB, NO_ITEM_NO_ABILITY, mode="deterministic") == (1, 10)
    assert resolve_hit_count(POPULATION_BOMB, WITH_LOADED_DICE, mode="deterministic") == (4, 10)


def test_bullet_seed_probabilistic_seed_yields_stable_hits() -> None:
    rng = RNG(42)

    assert [
        resolve_hit_count(BULLET_SEED, NO_ITEM_NO_ABILITY, mode="probabilistic", rng=rng)
        for _ in range(8)
    ] == [4, 2, 2, 5, 3, 2, 2, 2]


def test_population_bomb_probabilistic_seed_yields_stable_hits() -> None:
    rng = RNG(42)

    assert [
        resolve_hit_count(POPULATION_BOMB, NO_ITEM_NO_ABILITY, mode="probabilistic", rng=rng)
        for _ in range(5)
    ] == [4, 5, 3, 10, 6]


def test_bullet_seed_default_mean() -> None:
    mean = _mean(BULLET_SEED, NO_ITEM_NO_ABILITY)

    assert abs(mean - 3.10) < TOL


def test_bullet_seed_distribution_matches_showdown_weights() -> None:
    rng = RNG(42)
    counts = {2: 0, 3: 0, 4: 0, 5: 0}

    for _ in range(N):
        counts[resolve_hit_count(BULLET_SEED, NO_ITEM_NO_ABILITY, mode="probabilistic", rng=rng)] += 1

    assert abs(counts[2] / N - 0.35) < 0.03
    assert abs(counts[3] / N - 0.35) < 0.03
    assert abs(counts[4] / N - 0.15) < 0.03
    assert abs(counts[5] / N - 0.15) < 0.03


def test_loaded_dice_bullet_seed_probabilistic_distribution_is_4_or_5() -> None:
    rng = RNG(42)
    counts = {4: 0, 5: 0}

    for _ in range(N):
        hits = resolve_hit_count(BULLET_SEED, WITH_LOADED_DICE, mode="probabilistic", rng=rng)
        assert hits in {4, 5}
        counts[hits] += 1

    assert abs(counts[4] / N - 0.50) < 0.03
    assert abs(counts[5] / N - 0.50) < 0.03


def test_bullet_seed_skill_link_loaded_dice_fixed() -> None:
    rng = RNG(42)

    for _ in range(100):
        assert resolve_hit_count(BULLET_SEED, SKILL_LINK_LOADED_DICE, mode="probabilistic", rng=rng) == 5


def test_population_bomb_default_mean() -> None:
    mean = _mean(POPULATION_BOMB, NO_ITEM_NO_ABILITY)

    assert abs(mean - 6.5132) < 0.10


def test_population_bomb_loaded_dice_uniform() -> None:
    mean = _mean(POPULATION_BOMB, WITH_LOADED_DICE)

    assert abs(mean - 7.0) < TOL


def test_loaded_dice_population_bomb_uniform_4_to_10() -> None:
    rng = RNG(42)
    counts = {hits: 0 for hits in range(4, 11)}

    for _ in range(N):
        hits = resolve_hit_count(POPULATION_BOMB, WITH_LOADED_DICE, mode="probabilistic", rng=rng)
        assert 4 <= hits <= 10
        counts[hits] += 1

    for hits in range(4, 11):
        assert abs(counts[hits] / N - (1 / 7)) < TOL


def test_population_bomb_skill_link_probabilistic_still_10_hits() -> None:
    rng = RNG(42)

    for _ in range(100):
        assert resolve_hit_count(POPULATION_BOMB, WITH_SKILL_LINK, mode="probabilistic", rng=rng) == 10


def test_population_bomb_skill_link_loaded_dice_uses_loaded_dice_distribution() -> None:
    rng = RNG(42)
    observed = {
        resolve_hit_count(POPULATION_BOMB, SKILL_LINK_LOADED_DICE, mode="probabilistic", rng=rng)
        for _ in range(100)
    }

    assert observed <= set(range(4, 11))
    assert len(observed) > 1


def test_probabilistic_expected_alias_reserved_name_is_supported() -> None:
    rng = RNG(42)

    assert 1 <= resolve_hit_count(POPULATION_BOMB, NO_ITEM_NO_ABILITY, mode="expected", rng=rng) <= 10


def test_rng_rejects_invalid_random_bound() -> None:
    with pytest.raises(ValueError, match="n must be positive"):
        RNG(42).random(0)


def test_rng_rejects_empty_weight_total() -> None:
    with pytest.raises(ValueError, match="weights must sum to positive value"):
        RNG(42).weighted_choice([0, 0, 0])
