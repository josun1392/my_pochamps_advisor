import pytest
from llm.advisor_battle_state_context import build_deterministic_hit_chance_assessment


@pytest.mark.parametrize("accuracy,expected,reason", [(100, 100, "calculated_100_percent"), (80, 80, "stage_adjusted_accuracy")])
def test_neutral_accuracy_result(accuracy, expected, reason):
    result = build_deterministic_hit_chance_assessment({"move_id": "move", "accuracy": accuracy}, None)
    assert result["hit_chance_percent"] == expected and result["reason"] == reason


@pytest.mark.parametrize("accuracy", [0, 101, -1])
def test_invalid_accuracy_is_unavailable(accuracy):
    assert build_deterministic_hit_chance_assessment({"move_id": "move", "accuracy": accuracy}, None)["result"] == "unavailable"
