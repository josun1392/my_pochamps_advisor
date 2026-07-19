from llm.advisor_battle_state_context import build_direct_healing_assessment
def test_missing_hp_is_unavailable():
 assert build_direct_healing_assessment({"move_id":"recover","healing":50},None)["reason"]=="missing_attacker_hp"
