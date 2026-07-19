from llm.advisor_battle_state_context import build_target_hp_based_power_assessment
def test_ordinary_move_unaffected(): assert build_target_hp_based_power_assessment({"move_id":"tackle"},None) is None
