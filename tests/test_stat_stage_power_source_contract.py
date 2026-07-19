from llm.advisor_battle_state_context import build_stat_stage_based_power_assessment
def test_missing_stages_unavailable(): assert build_stat_stage_based_power_assessment({"move_id":"stored-power"},None)["reason"]=="missing_self_stat_stages"
