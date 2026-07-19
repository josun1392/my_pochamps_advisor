from llm.advisor_battle_state_context import build_multi_hit_assessment

def test_fixed_two_hit_uses_independent_roll_convolution():
    r=build_multi_hit_assessment({"calculation_status":"resolved","damage_rolls":[10,12]*8},{"move_id":"double-kick","min_hits":2,"max_hits":2},None)
    assert r["total_damage_range"] == {"minimum":20,"maximum":24}
