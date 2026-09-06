from llm.advisor_battle_state_context import build_positive_stage_sum_power_assessment
def test_zero_stages_resolve_base_power(): assert build_positive_stage_sum_power_assessment({"move_id":"stored-power"},{"current_stages":[{"side":"self","stat":s,"stage":0} for s in ("attack","defense","special-attack","special-defense","speed","accuracy","evasion")]})["effective_power"]==20
