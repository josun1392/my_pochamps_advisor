from llm.advisor_battle_state_context import build_multi_hit_drain_recoil_assessment
def test_hit_by_hit_damage_stops_at_hp():
 h={"current_hp":[{"side":"opponent","current_hp":100,"maximum_hp":100}]}
 r=build_multi_hit_drain_recoil_assessment({"calculation_status":"resolved","damage_rolls":[70]*16},{"move_id":"x","min_hits":3,"max_hits":3,"drain":50},h)
 assert r["actual_damage_range"]=={"minimum":100,"maximum":100}
