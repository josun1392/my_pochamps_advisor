from llm.advisor_battle_state_context import build_environment_based_move_assessment
def test_ungrounded_terrain_is_untransformed():
 r=build_environment_based_move_assessment({"move_id":"terrain-pulse"},{"current_field":{"terrain":"electric"}},False)
 assert (r["effective_type"],r["effective_power"])==("normal",50)
