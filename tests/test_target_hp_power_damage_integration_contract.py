from llm.advisor_battle_state_context import build_deterministic_calculation_context
def test_missing_target_hp_no_fallback():
 r=build_deterministic_calculation_context(None,selected_move={"move_id":"crush-grip","power":120})
 assert r["target_hp_based_power_assessment"]["status"]=="unavailable"
