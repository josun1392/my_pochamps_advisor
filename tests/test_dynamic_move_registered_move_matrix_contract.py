from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY
def test_ten_families_have_registered_moves(): assert len(set(DYNAMIC_MOVE_ASSESSMENT_REGISTRY.values())) == 10
