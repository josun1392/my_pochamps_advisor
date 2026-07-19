from llm.advisor_battle_state_context import build_multi_hit_assessment

def test_multi_hit_ko_and_zero_hp_boundary():
    hp={"current_hp":[{"side":"opponent","current_hp":20,"maximum_hp":100}]}
    r=build_multi_hit_assessment({"calculation_status":"resolved","damage_rolls":[10]*16},{"move_id":"double-kick","min_hits":2,"max_hits":2},hp)
    assert r["ko_status"] == "guaranteed_ko"
