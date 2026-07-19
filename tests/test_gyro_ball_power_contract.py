from llm.advisor_battle_state_context import build_speed_based_power_assessment
def _final(a,b): return {"current_final_stats":[{"side":"self","stat":"speed","value":a,"status":"user_confirmed","source":"user_confirmed_final_battle_stat"},{"side":"opponent","stat":"speed","value":b,"status":"user_confirmed","source":"user_confirmed_final_battle_stat"}]}
def test_floor_and_cap():
 assert build_speed_based_power_assessment({"move_id":"gyro-ball"},_final(100,100),None,None)["effective_power"]==26
 assert build_speed_based_power_assessment({"move_id":"gyro-ball"},_final(10,1000),None,None)["effective_power"]==150
