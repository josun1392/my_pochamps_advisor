from pathlib import Path
def test_design_forbids_implementation():
    assert 'No provider, UI\norchestration, evaluator, or Turn Engine implementation is authorized' in Path('docs/spike_v14.1_battle_advisor_integration_architecture.md').read_text()
