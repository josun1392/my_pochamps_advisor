import pytest
from llm.advisor_battle_state_context import DYNAMIC_MOVE_PRODUCTION_COVERAGE, validate_dynamic_move_production_coverage
def test_family_drift_rejected():
    bad={k:dict(v) for k,v in DYNAMIC_MOVE_PRODUCTION_COVERAGE.items()}; bad['eruption']['family']='speed_based_power'
    with pytest.raises(ValueError): validate_dynamic_move_production_coverage(bad)
