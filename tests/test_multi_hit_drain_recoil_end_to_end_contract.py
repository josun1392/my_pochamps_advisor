from llm.advisor_battle_state_context import build_multi_hit_drain_recoil_assessment
def test_variable_multi_hit_combined_result():
 h={"current_hp":[{"side":"opponent","current_hp":100,"maximum_hp":100}]}
 r=build_multi_hit_drain_recoil_assessment({"calculation_status":"resolved","damage_rolls":[10]*16},{"move_id":"x","min_hits":2,"max_hits":5,"drain":50},h)
 assert r["hit_count_type"]=="variable" and r["effect"]=="drain"
