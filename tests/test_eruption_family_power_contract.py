import pytest
from llm.advisor_battle_state_context import build_current_hp_based_power_assessment
def _hp(current, maximum): return {"current_hp":[{"side":"self","current_hp":current,"maximum_hp":maximum}]}
@pytest.mark.parametrize("move",["eruption","water-spout","dragon-energy"])
def test_full_hp_is_150(move): assert build_current_hp_based_power_assessment({"move_id":move},_hp(100,100))["effective_power"]==150
def test_proportional_floor_and_minimum_one():
 assert build_current_hp_based_power_assessment({"move_id":"eruption"},_hp(81,161))["effective_power"]==75
 assert build_current_hp_based_power_assessment({"move_id":"eruption"},_hp(1,300))["effective_power"]==1
