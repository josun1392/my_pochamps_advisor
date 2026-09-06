import pytest
from llm.advisor_battle_state_context import build_target_weight_power_assessment
@pytest.mark.parametrize("weight,power",[(99,20),(100,40),(250,60),(500,80),(1000,100),(2000,120)])
@pytest.mark.parametrize("move",["grass-knot","low-kick"])
def test_absolute_brackets(move,weight,power): assert build_target_weight_power_assessment({"move_id":move},{"opponent_weight":weight})["effective_power"]==power
