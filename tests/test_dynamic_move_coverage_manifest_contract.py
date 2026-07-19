from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY, DYNAMIC_MOVE_PRODUCTION_COVERAGE, validate_dynamic_move_production_coverage
def test_manifest_covers_registry():
    assert len(DYNAMIC_MOVE_ASSESSMENT_REGISTRY) == len(DYNAMIC_MOVE_PRODUCTION_COVERAGE) == 30
    validate_dynamic_move_production_coverage()
