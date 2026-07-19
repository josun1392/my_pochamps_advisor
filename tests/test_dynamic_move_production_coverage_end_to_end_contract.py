from llm.advisor_battle_state_context import DYNAMIC_MOVE_PRODUCTION_COVERAGE
def test_rows_have_key_and_scope(): assert all(x['assessment_key'].endswith('_assessment') and x['scope'] for x in DYNAMIC_MOVE_PRODUCTION_COVERAGE.values())
