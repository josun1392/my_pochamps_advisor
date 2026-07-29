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
    return {"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [{"kind": "damage", "claim": "deterministic mechanics evidence"}], "risks": [], "alternatives": [], "grounding": grounding}


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
