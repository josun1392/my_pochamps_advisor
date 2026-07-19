from llm.advisor_battle_state_context import build_stat_stage_based_power_assessment
def test_punishment_cap():
 r=build_stat_stage_based_power_assessment({"move_id":"punishment"},{"current_stages":[{"side":"opponent","stat":"attack","stage":6}]*3})
 assert r["effective_power"]==200
