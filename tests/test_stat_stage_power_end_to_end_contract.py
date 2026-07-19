from llm.advisor_battle_state_context import build_stat_stage_based_power_assessment
def test_zero_stages_resolve_base_power(): assert build_stat_stage_based_power_assessment({"move_id":"stored-power"},{"current_stages":[{"side":"self","stat":"speed","stage":0}]})["effective_power"]==20
