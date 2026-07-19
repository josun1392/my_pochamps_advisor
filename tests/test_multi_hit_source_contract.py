from llm.advisor_battle_state_context import build_multi_hit_assessment

def test_single_hit_has_no_assessment_and_invalid_metadata_is_unavailable():
    assert build_multi_hit_assessment({"calculation_status":"resolved","damage_rolls":[10]*16},{"move_id":"tackle"},None) is None
    assert build_multi_hit_assessment({"calculation_status":"resolved","damage_rolls":[10]*16},{"move_id":"x","min_hits":5,"max_hits":2},None)["calculation_status"] == "unavailable"
