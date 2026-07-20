from pathlib import Path
from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY


def test_closure_names_all_registered_moves():
    text=Path('docs/v13_dynamic_move_phase_closure.md').read_text(encoding='utf-8')
    assert all(move in text for move in DYNAMIC_MOVE_ASSESSMENT_REGISTRY)
    assert 'one registry-selected resolver' in text
    assert 'without metadata power or\ntype fallback' in text
    assert 'Only the environment family may override effective type' in text
    assert 'ten-family/30-move\ninventory' in text
