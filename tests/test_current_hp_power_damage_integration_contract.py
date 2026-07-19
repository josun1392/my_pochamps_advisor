from llm.advisor_battle_state_context import build_deterministic_calculation_context
def test_missing_hp_prevents_variable_power_damage_fallback():
 r=build_deterministic_calculation_context(None,selected_move={"move_id":"eruption","category":"special","power":150,"type":"fire"})
 assert r["current_hp_based_power_assessment"]["status"]=="unavailable" and "damage_estimates" not in r
