from llm.advisor_battle_state_context import build_stat_stage_based_power_assessment
def test_ordinary_move_no_assessment(): assert build_stat_stage_based_power_assessment({"move_id":"tackle"},None) is None
