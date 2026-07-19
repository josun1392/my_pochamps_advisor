import pytest
from llm.advisor_battle_state_context import build_current_hp_based_power_assessment

def test_missing_invalid_and_fainted_hp_are_not_resolved():
    assert build_current_hp_based_power_assessment({"move_id":"eruption"}, None)["reason"] == "missing_self_current_hp"
    assert build_current_hp_based_power_assessment({"move_id":"eruption"}, {"current_hp":[{"side":"self","current_hp":0,"maximum_hp":100}]})["reason"] == "user_already_fainted"
    assert build_current_hp_based_power_assessment({"move_id":"eruption"}, {"current_hp":[{"side":"self","current_hp":True,"maximum_hp":100}]})["reason"] == "invalid_self_hp_context"

def test_ordinary_move_has_no_assessment(): assert build_current_hp_based_power_assessment({"move_id":"tackle"}, None) is None
