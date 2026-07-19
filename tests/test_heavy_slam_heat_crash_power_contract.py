import pytest
from llm.advisor_battle_state_context import build_weight_based_power_assessment
@pytest.mark.parametrize("move",["heavy-slam","heat-crash"])
@pytest.mark.parametrize("self_weight,power",[(100,40),(200,60),(300,80),(400,100),(500,120)])
def test_ratio_brackets(move,self_weight,power): assert build_weight_based_power_assessment({"move_id":move},{"self_weight":self_weight,"opponent_weight":100})["effective_power"]==power
