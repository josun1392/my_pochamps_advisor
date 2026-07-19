from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY


def test_registry_prevents_cross_family_dispatch_by_identity():
    assert DYNAMIC_MOVE_ASSESSMENT_REGISTRY["rage-fist"] != DYNAMIC_MOVE_ASSESSMENT_REGISTRY["fury-cutter"]
