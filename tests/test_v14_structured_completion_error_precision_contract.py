from llm.advisor_candidate_contract import _validate_claim
import pytest


def test_claim_contradiction_keeps_precise_sanitized_code():
    with pytest.raises(ValueError, match="claim_evidence_contradiction"):
        _validate_claim({"kind": "partial_context", "claim": "missing evidence"}, {"status": "resolved"})
