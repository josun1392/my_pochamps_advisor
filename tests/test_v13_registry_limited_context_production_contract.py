from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_deterministic_calculation_context


REGISTERED_MOVES = (
    ("eruption", "current_hp_based_power_assessment"), ("water-spout", "current_hp_based_power_assessment"), ("dragon-energy", "current_hp_based_power_assessment"), ("flail", "current_hp_based_power_assessment"), ("reversal", "current_hp_based_power_assessment"),
    ("electro-ball", "speed_based_power_assessment"), ("gyro-ball", "speed_based_power_assessment"),
    ("heavy-slam", "weight_based_power_assessment"), ("heat-crash", "weight_based_power_assessment"), ("grass-knot", "weight_based_power_assessment"), ("low-kick", "weight_based_power_assessment"),
    ("stored-power", "stat_stage_based_power_assessment"), ("power-trip", "stat_stage_based_power_assessment"), ("punishment", "stat_stage_based_power_assessment"),
    ("crush-grip", "target_hp_based_power_assessment"), ("wring-out", "target_hp_based_power_assessment"),
    ("weather-ball", "environment_based_move_assessment"), ("terrain-pulse", "environment_based_move_assessment"),
    ("facade", "binary_condition_power_assessment"), ("hex", "binary_condition_power_assessment"), ("venoshock", "binary_condition_power_assessment"), ("brine", "binary_condition_power_assessment"),
    ("avalanche", "turn_event_power_assessment"), ("revenge", "turn_event_power_assessment"), ("payback", "turn_event_power_assessment"), ("assurance", "turn_event_power_assessment"),
    ("rage-fist", "battle_counter_power_assessment"), ("last-respects", "battle_counter_power_assessment"),
    ("fury-cutter", "consecutive_use_power_assessment"), ("echoed-voice", "consecutive_use_power_assessment"),
)


def test_independent_fixture_covers_thirty_canonical_moves_and_ten_families() -> None:
    assert len(REGISTERED_MOVES) == 30
    assert len({key for _, key in REGISTERED_MOVES}) == 10
    assert len({move for move, _ in REGISTERED_MOVES}) == 30


@pytest.mark.parametrize(("move_id", "assessment_key"), REGISTERED_MOVES)
def test_all_registered_moves_fail_closed_without_required_limited_context(move_id: str, assessment_key: str) -> None:
    result = build_deterministic_calculation_context(None, selected_move={"move_id": move_id, "power": 999, "type": "dragon"})

    assert result is not None
    assessment = result[assessment_key]
    assert assessment["status"] != "resolved"
    assert assessment.get("effective_power") != 999
    assert assessment.get("effective_type") != "dragon"
    assert set(result) == {assessment_key}
