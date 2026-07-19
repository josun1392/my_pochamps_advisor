from llm.advisor_battle_state_context import build_multi_hit_assessment

def test_exceptional_multi_hit_remains_unavailable():
    r=build_multi_hit_assessment({"calculation_status":"resolved","damage_rolls":[10]*16},{"move_id":"population-bomb","min_hits":2,"max_hits":5},None)
    assert r["reason"] == "unsupported_multi_hit_rule"
