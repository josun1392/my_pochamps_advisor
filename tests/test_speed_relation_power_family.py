from llm.advisor_battle_state_context import build_speed_based_power_assessment
from advisor.canonical_speed_relation_power_family import resolve_canonical_speed_relation_power_move
def _final(a,b):return {"current_final_stats":[{"side":"self","stat":"speed","value":a,"status":"user_confirmed","source":"user_confirmed_final_battle_stat"},{"side":"opponent","stat":"speed","value":b,"status":"user_confirmed","source":"user_confirmed_final_battle_stat"}]}
def test_exact_integer_electro_and_gyro_boundaries():
 e=lambda a,b:build_speed_based_power_assessment({"move_id":"electro-ball"},_final(a,b),None,None)["effective_power"]
 g=lambda a,b:build_speed_based_power_assessment({"move_id":"gyro-ball"},_final(a,b),None,None)["effective_power"]
 assert [e(*x) for x in ((99,100),(100,100),(200,100),(300,100),(400,100),(401,100))]==[40,60,80,120,150,150]
 assert [g(*x) for x in ((100,100),(100,200),(3,10),(10,1000))]==[26,51,84,150]
 assert resolve_canonical_speed_relation_power_move(move={"move_id":"electro-ball"})["effect"]["contact"] is False
 assert resolve_canonical_speed_relation_power_move(move={"move_id":"gyro-ball"})["effect"]["contact"] is True
