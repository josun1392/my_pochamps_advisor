from pathlib import Path
def test_closure_documents_canonical_counts_and_v14_boundary():
    text=Path('docs/v13_dynamic_move_phase_closure.md').read_text(encoding='utf-8')
    assert 'ten families and 30' in text and 'No v14 implementation is authorized' in text
