from llm.advisor_battle_state_context import build_speed_based_power_assessment
def test_missing_final_speed_is_unavailable(): assert build_speed_based_power_assessment({"move_id":"electro-ball"},None,None,None)["reason"]=="missing_self_final_speed"
