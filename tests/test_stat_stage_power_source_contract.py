from llm.advisor_battle_state_context import build_positive_stage_sum_power_assessment
def test_missing_stages_unavailable(): assert build_positive_stage_sum_power_assessment({"move_id":"stored-power"},None)["reason"]=="missing_self_stat_stages"
