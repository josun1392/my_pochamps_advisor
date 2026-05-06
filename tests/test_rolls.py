from __future__ import annotations

from advisor.damage.rolls import calc_ko_chance


def test_guaranteed_ohko() -> None:
    result = calc_ko_chance([100] * 16, defender_hp=100)

    assert result.n_hits == 1
    assert result.chance == 1.0
    assert result.description == "guaranteed OHKO"


def test_partial_ohko_chance() -> None:
    result = calc_ko_chance([90] * 8 + [100] * 8, defender_hp=100)

    assert result.n_hits == 1
    assert result.chance == 0.5


def test_guaranteed_2hko() -> None:
    result = calc_ko_chance([60] * 16, defender_hp=100)

    assert result.n_hits == 2
    assert result.chance == 1.0


def test_possible_2hko_chance() -> None:
    result = calc_ko_chance([40] * 8 + [60] * 8, defender_hp=100)

    assert result.n_hits == 2
    assert result.chance == 0.75


def test_current_hp_override() -> None:
    result = calc_ko_chance([50] * 16, defender_hp=100, defender_current_hp=50)

    assert result.n_hits == 1
    assert result.chance == 1.0
