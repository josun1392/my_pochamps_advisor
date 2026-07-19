from llm.advisor_battle_state_context import build_multi_hit_assessment

def test_variable_two_to_five_has_full_range():
    r=build_multi_hit_assessment({"calculation_status":"resolved","damage_rolls":[10]*16},{"move_id":"bullet-seed","min_hits":2,"max_hits":5},None)
    assert r["hit_count_type"] == "variable" and r["total_damage_range"] == {"minimum":20,"maximum":50}
