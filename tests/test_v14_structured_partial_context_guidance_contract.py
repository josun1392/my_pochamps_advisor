from llm.advisor_client import _STRUCTURED_SEMANTIC_GUIDANCE


def test_global_limitations_are_not_candidate_specific_missing_evidence():
    assert "global limitations" in _STRUCTURED_SEMANTIC_GUIDANCE
