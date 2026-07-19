import pytest
from llm.advisor_battle_state_context import build_binary_condition_power_assessment


@pytest.mark.parametrize("condition", ["burn", "poison", "toxic", "paralysis"])
def test_facade_conditions_double(condition):
    context = {"current_conditions": [{"side": "self", "condition_type": condition}]}
    assert build_binary_condition_power_assessment({"move_id": "facade"}, context, None)["effective_power"] == 140


def test_facade_sleep_does_not_double():
    context = {"current_conditions": [{"side": "self", "condition_type": "sleep"}]}
    assert build_binary_condition_power_assessment({"move_id": "facade"}, context, None)["effective_power"] == 70
