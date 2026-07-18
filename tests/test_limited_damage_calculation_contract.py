from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_limited_damage_estimate


@pytest.mark.parametrize(
    ("move", "stats", "expected"),
    [
        ({"move_id": "tackle", "category": "physical", "power": 80}, [{"side": "self", "stat": "attack", "effective_value": 200}, {"side": "opponent", "stat": "defense", "effective_value": 150}], (40, 48)),
        ({"move_id": "thunderbolt", "category": "special", "power": 90}, [{"side": "self", "stat": "special-attack", "effective_value": 205}, {"side": "opponent", "stat": "special-defense", "effective_value": 180}], (39, 47)),
    ],
)
def test_physical_and_special_damage_reuse_base_formula_and_raw_roll_range(move: dict[str, object], stats: list[dict[str, object]], expected: tuple[int, int]) -> None:
    estimate = build_limited_damage_estimate(stats, move)
    assert estimate is not None
    assert (estimate["min_damage"], estimate["max_damage"]) == expected
    assert estimate["calculation_status"] == "resolved"


@pytest.mark.parametrize(
    ("move", "status", "reason"),
    [
        ({"move_id": "swords-dance", "category": "status", "power": None}, "unsupported_move", "status_move"),
        ({"move_id": "gyro-ball", "category": "physical", "power": 1}, "unsupported_move", "variable_power"),
        ({"move_id": "seismic-toss", "category": "physical", "power": 1}, "unsupported_move", "fixed_damage"),
        ({"move_id": "rock-blast", "category": "physical", "power": 25}, "unsupported_move", "multi_hit_unresolved"),
        ({"move_id": "tackle", "category": "physical", "power": None}, "unavailable", "missing_move_power"),
    ],
)
def test_unsupported_or_incomplete_move_metadata_never_gets_a_range(move: dict[str, object], status: str, reason: str) -> None:
    estimate = build_limited_damage_estimate([], move)
    assert estimate is not None
    assert estimate["calculation_status"] == status
    assert estimate["reason"] == reason
    assert "min_damage" not in estimate
