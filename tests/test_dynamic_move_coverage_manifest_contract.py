from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY, DYNAMIC_MOVE_PRODUCTION_COVERAGE, validate_dynamic_move_production_coverage
def test_manifest_covers_registry():
    assert len(DYNAMIC_MOVE_ASSESSMENT_REGISTRY) == len(DYNAMIC_MOVE_PRODUCTION_COVERAGE) == 31
    assert DYNAMIC_MOVE_ASSESSMENT_REGISTRY["hard-press"] == "target_hp_based_power"
    assert DYNAMIC_MOVE_PRODUCTION_COVERAGE["hard-press"]["assessment_key"] == "target_hp_based_power_assessment"
    validate_dynamic_move_production_coverage()
