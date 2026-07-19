from llm.advisor_battle_state_context import build_direct_healing_assessment
def test_missing_or_zero_healing_has_no_result():
 assert build_direct_healing_assessment({"move_id":"x","healing":0},None) is None
