from llm.structured_fixture_evaluation import evaluate_structured_fixture, get_fixed_fixture_catalog


def _fixture(name):
    return next(item for item in get_fixed_fixture_catalog() if item["fixture_id"] == name)


def test_resolved_and_partial_context_fixtures_reuse_completion_and_presentation_contracts():
    resolved = evaluate_structured_fixture(fixture=_fixture("clear_resolved"))
    partial = evaluate_structured_fixture(fixture=_fixture("partial_context_valid"))
    assert resolved["completion_status"] == "resolved" and resolved["recommended_pair_match"] and resolved["presentation_status"] == "resolved"
    assert partial["completion_status"] == "insufficient_context" and partial["semantic_success"] and partial["recommended_pair_match"]


def test_slot_mismatch_invalid_alternative_and_claim_failures_keep_sanitized_codes_and_evidence():
    mismatch = evaluate_structured_fixture(fixture=_fixture("slot_mismatch"))
    alternative = evaluate_structured_fixture(fixture=_fixture("invalid_alternative"))
    claim = evaluate_structured_fixture(fixture=_fixture("unsupported_claim"))
    assert mismatch["failure_codes"] == ["recommended_candidate_not_selectable"]
    assert alternative["failure_codes"] == ["selection outside selectable exact-set"]
    assert claim["failure_codes"] == ["invalid_claim"]
    assert all(result["evidence_preserved"] and result["presentation_status"] == "validation_failed" for result in (mismatch, alternative, claim))
