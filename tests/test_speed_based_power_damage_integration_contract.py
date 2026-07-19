from llm.advisor_battle_state_context import build_deterministic_calculation_context
def test_missing_speed_does_not_fallback_to_metadata_power():
 r=build_deterministic_calculation_context(None,selected_move={"move_id":"electro-ball","power":80,"category":"special"})
 assert r["speed_based_power_assessment"]["status"]=="unavailable"
