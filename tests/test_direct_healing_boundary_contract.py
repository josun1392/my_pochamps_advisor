from llm.advisor_battle_state_context import build_direct_healing_assessment
def test_full_hp_fainted_and_unsupported_boundaries():
 assert build_direct_healing_assessment({"move_id":"recover","healing":50},{"current_hp":[{"side":"self","current_hp":100,"maximum_hp":100}]})["status"]=="no_effect"
 assert build_direct_healing_assessment({"move_id":"synthesis","healing":50},{"current_hp":[{"side":"self","current_hp":50,"maximum_hp":100}]})["reason"]=="unsupported_direct_healing_rule"
