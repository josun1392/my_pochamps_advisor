from llm.advisor_battle_state_context import build_environment_based_move_assessment
def test_ordinary_move_is_unchanged(): assert build_environment_based_move_assessment({"move_id":"tackle"},None) is None
