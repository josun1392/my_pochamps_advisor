from llm.advisor_battle_state_context import build_weight_based_power_assessment
def test_ordinary_move_has_no_weight_result(): assert build_weight_based_power_assessment({"move_id":"tackle"},None) is None
