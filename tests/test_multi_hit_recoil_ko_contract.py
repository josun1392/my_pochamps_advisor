from llm.advisor_battle_state_context import build_multi_hit_drain_recoil_assessment
def test_multi_hit_recoil_ko():
 h={"current_hp":[{"side":"opponent","current_hp":100,"maximum_hp":100},{"side":"self","current_hp":20,"maximum_hp":100}]}
 r=build_multi_hit_drain_recoil_assessment({"calculation_status":"resolved","damage_rolls":[50]*16},{"move_id":"x","min_hits":2,"max_hits":2,"drain":-25},h)
 assert r["recoil_ko_status"]=="guaranteed_recoil_ko"
