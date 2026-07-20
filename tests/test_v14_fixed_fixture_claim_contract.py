from llm.advisor_client import _STRUCTURED_SEMANTIC_GUIDANCE
from llm.structured_fixture_evaluation import evaluate_structured_fixture, get_fixed_fixture_catalog


def _fixture(name):
    return next(item for item in get_fixed_fixture_catalog() if item["fixture_id"] == name)


def test_guidance_makes_the_claim_shape_and_global_limitation_boundary_explicit():
    assert "exactly a kind/claim object" in _STRUCTURED_SEMANTIC_GUIDANCE
    assert "supported claim kinds" in _STRUCTURED_SEMANTIC_GUIDANCE
    assert "global limitations" in _STRUCTURED_SEMANTIC_GUIDANCE


def test_partial_context_contradiction_remains_rejected_without_broadening_claim_schema():
    result = evaluate_structured_fixture(fixture=_fixture("partial_context_contradiction"))
    assert result["completion_status"] == "response_validation_failed"
    assert result["failure_codes"] == ["claim_evidence_contradiction"]
