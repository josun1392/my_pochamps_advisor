from llm.advisor_battle_state_context import DYNAMIC_MOVE_PRODUCTION_COVERAGE
def test_environment_only_type_override(): assert all(x['type_override'] == (x['family'] == 'environment_based_move') for x in DYNAMIC_MOVE_PRODUCTION_COVERAGE.values())
