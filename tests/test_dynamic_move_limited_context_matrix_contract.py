from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY, resolve_registered_dynamic_move
def test_gate_off_omits_registered_moves(): assert all(resolve_registered_dynamic_move({'move_id': m}, limited_context_enabled=False) is None for m in DYNAMIC_MOVE_ASSESSMENT_REGISTRY)
