from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_deterministic_calculation_context


@pytest.mark.parametrize(("move_id", "assessment_key"), [
    ("eruption", "current_hp_based_power_assessment"), ("electro-ball", "speed_based_power_assessment"),
    ("heavy-slam", "weight_based_power_assessment"), ("stored-power", "stat_stage_based_power_assessment"),
    ("crush-grip", "target_hp_based_power_assessment"), ("weather-ball", "environment_based_move_assessment"),
    ("facade", "binary_condition_power_assessment"), ("avalanche", "turn_event_power_assessment"),
    ("rage-fist", "battle_counter_power_assessment"), ("fury-cutter", "consecutive_use_power_assessment"),
])
def test_registered_move_with_missing_context_does_not_use_metadata(move_id: str, assessment_key: str) -> None:
    result = build_deterministic_calculation_context(None, selected_move={"move_id": move_id, "power": 999, "type": "dragon"})

    assert result is not None
    assert result[assessment_key]["status"] != "resolved"
    assert result[assessment_key].get("effective_power") != 999
    assert set(result) == {assessment_key}
