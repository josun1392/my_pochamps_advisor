from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY, DYNAMIC_MOVE_PRODUCTION_COVERAGE
def test_v13_inventory_is_eleven_families_and_thirty_moves():
    assert len(set(DYNAMIC_MOVE_ASSESSMENT_REGISTRY.values())) == 12
    assert len(DYNAMIC_MOVE_ASSESSMENT_REGISTRY) == 30
    assert set(DYNAMIC_MOVE_ASSESSMENT_REGISTRY) == set(DYNAMIC_MOVE_PRODUCTION_COVERAGE)
