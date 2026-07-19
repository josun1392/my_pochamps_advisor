import pytest
from llm.advisor_battle_state_context import build_speed_based_power_assessment
def _final(a,b): return {"current_final_stats":[{"side":"self","stat":"speed","value":a,"status":"user_confirmed","source":"user_confirmed_final_battle_stat"},{"side":"opponent","stat":"speed","value":b,"status":"user_confirmed","source":"user_confirmed_final_battle_stat"}]}
@pytest.mark.parametrize("a,b,p",[(50,100,40),(100,100,60),(200,100,80),(300,100,120),(400,100,150)])
def test_brackets(a,b,p): assert build_speed_based_power_assessment({"move_id":"electro-ball"},_final(a,b),None,None)["effective_power"]==p
