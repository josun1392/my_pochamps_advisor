from llm.advisor_battle_state_context import build_direct_healing_assessment
def test_floor_and_cap():
 h={"current_hp":[{"side":"self","current_hp":221,"maximum_hp":301}]}
 r=build_direct_healing_assessment({"move_id":"recover","healing":50},h)
 assert r["raw_healing"]==150 and r["actual_healing"]==80 and r["resulting_hp"]==301
