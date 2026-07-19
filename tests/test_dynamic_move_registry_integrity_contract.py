import pytest
from llm.advisor_battle_state_context import DYNAMIC_MOVE_ASSESSMENT_REGISTRY, validate_dynamic_move_assessment_registry


def test_builtin_registry_is_valid():
    validate_dynamic_move_assessment_registry()


def test_unknown_or_drifted_family_is_rejected():
    bad = dict(DYNAMIC_MOVE_ASSESSMENT_REGISTRY); bad["tackle"] = "unknown"
    with pytest.raises(ValueError): validate_dynamic_move_assessment_registry(bad)
