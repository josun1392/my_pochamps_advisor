from scripts.run_sanitized_direct_mechanics_smoke import EXIT, FIXTURES, _prepared, run_smoke


def _response(payload):
    mechanics = payload["candidate_comparisons"][0]["mechanics_result"]
    grounding = {
        "schema_version": "grounding-v1",
        "confirmed_facts": [],
        "unknown_facts": [],
        "evidence_only": [{"path": "candidate_comparisons.0.mechanics_result", "authority": "evidence", "source": "deterministic"}],
        "conflicts": [],
        "conditional_dependencies": ([{"path": "candidate_comparisons.0.mechanics_result.missing_inputs"}] if mechanics["status"] == "insufficient_context" else []),
    }
    if mechanics["status"] == "insufficient_context":
        return {"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [{"kind": "partial_context", "claim": "deterministic mechanics is incomplete"}], "risks": [], "alternatives": [], "grounding": grounding}
    return {"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [{"kind": "mechanics", "claim": "deterministic mechanics evidence"}], "risks": [], "alternatives": [], "grounding": grounding}


def test_fixture_preparation_produces_known_and_insufficient_mechanics_evidence():
    assert _prepared(FIXTURES[0])["candidates"][0]["mechanics_result"]["status"] == "known"
    incomplete = _prepared(FIXTURES[1])["candidates"][0]["mechanics_result"]
    assert incomplete["status"] == "insufficient_context"
    assert incomplete["damage_range"] is None and incomplete["ko_result"] is None


def test_fake_provider_requires_value_free_mechanics_acknowledgement_and_preserves_insufficient_status():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"]
    assert result["provider_calls"] == 2

    def missing_ack(payload):
        response = _response(payload)
        response["grounding"]["evidence_only"] = []
        return response

    failed = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=missing_ack)
    assert failed["exit_code"] == EXIT["semantic"]
    assert failed["provider_calls"] == 1
    assert failed["diagnostic"] == "mechanics_result_unacknowledged"


def test_provider_failure_exposes_only_allowlisted_sanitized_code():
    class Timeout(Exception):
        code = "provider_timeout"

    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=lambda _: (_ for _ in ()).throw(Timeout()))
    assert result["exit_code"] == EXIT["provider"]
    assert result["diagnostic"] == "provider_timeout"


def test_known_mechanics_claim_is_allowed_but_numeric_or_insufficient_mechanics_claims_are_rejected():
    import pytest
    from llm.advisor_candidate_contract import _validate_claim, complete_recommendation_cycle

    complete = _prepared(FIXTURES[0])
    accepted = complete_recommendation_cycle(prepared_cycle=complete, response_payload=_response(complete["recommendation_request"]))
    assert accepted["status"] == "resolved"

    numeric = _response(complete["recommendation_request"])
    numeric["primary_reasons"] = [{"kind": "mechanics", "claim": "50 damage"}]
    assert complete_recommendation_cycle(prepared_cycle=complete, response_payload=numeric)["errors"] == ["mechanics_numeric_claim_without_evidence"]

    incomplete = _prepared(FIXTURES[1])
    with pytest.raises(ValueError, match="mechanics_claim_on_insufficient_context"):
        _validate_claim({"kind": "mechanics", "claim": "deterministic mechanics"}, incomplete["candidates"][0])
