def test_dynamic_integration_is_explicitly_deferred_to_existing_resolver():
    from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY
    assert len(DYNAMIC_MOVE_ASSESSMENT_REGISTRY)==30
