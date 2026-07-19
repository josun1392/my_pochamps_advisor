from llm.advisor_battle_state_context import build_environment_based_move_assessment
def test_invalid_environment_rejected(): assert build_environment_based_move_assessment({"move_id":"weather-ball"},{"current_field":{"weather":"fog"}})["status"]=="unavailable"
