from llm.advisor_battle_state_context import build_hp_based_special_damage_assessment
def test_final_gambit_ghost_immunity_still_has_self_faint():
 h={"current_hp":[{"side":"self","current_hp":80,"maximum_hp":100},{"side":"opponent","current_hp":100,"maximum_hp":100}]}; r=build_hp_based_special_damage_assessment({"move_id":"final-gambit"},h,{"opponent_active":{"types":["ghost"]}}); assert r["actual_damage"]==0 and r["self_faint_status"]=="guaranteed_self_faint"
