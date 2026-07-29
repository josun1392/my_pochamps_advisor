from scripts.run_sanitized_direct_mechanics_smoke import EXIT, FIXTURES, _prepared, run_smoke


def _response(payload):
    mechanics = payload["candidate_comparisons"][0]["mechanics_result"]
    acknowledgement = {
        "slot_index": 0,
        "move": "tackle",
        "mechanics_path": "candidate_comparisons.0.mechanics_result",
        "status": mechanics["status"],
        "missing_inputs_path": "candidate_comparisons.0.mechanics_result.missing_inputs" if mechanics["status"] == "insufficient_context" else None,
    }
    grounding = {
        "schema_version": "grounding-v1",
        "confirmed_facts": [],
        "unknown_facts": [],
        "evidence_only": [],
        "conflicts": [],
        "conditional_dependencies": ([{"path": "candidate_comparisons.0.mechanics_result.missing_inputs"}] if mechanics["status"] == "insufficient_context" else []),
    }
    if mechanics["status"] == "insufficient_context":
        return {"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [{"kind": "partial_context", "claim": "deterministic mechanics is incomplete"}], "risks": [], "alternatives": [], "grounding": grounding, "mechanics_acknowledgements": [acknowledgement]}
    return {"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [{"kind": "mechanics", "claim": "deterministic mechanics evidence"}], "risks": [], "alternatives": [], "grounding": grounding, "mechanics_acknowledgements": [acknowledgement]}


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
        del response["mechanics_acknowledgements"]
        return response

    failed = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=missing_ack)
    assert failed["exit_code"] == EXIT["semantic"]
    assert failed["provider_calls"] == 1
    assert failed["diagnostic"] == "mechanics_acknowledgement_missing"

    def wrong_path(payload):
        response = _response(payload)
        response["mechanics_acknowledgements"][0]["mechanics_path"] = "candidate_comparisons.1.mechanics_result"
        return response

    wrong_path_failed = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=wrong_path)
    assert wrong_path_failed["exit_code"] == EXIT["semantic"]
    assert wrong_path_failed["diagnostic"] == "mechanics_acknowledgement_path_invalid"

    def wrong_dependency(payload):
        response = _response(payload)
        if response["mechanics_acknowledgements"][0]["status"] == "insufficient_context":
            response["mechanics_acknowledgements"][0]["missing_inputs_path"] = None
        return response

    dependency_failed = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=wrong_dependency)
    assert dependency_failed["exit_code"] == EXIT["semantic"]
    assert dependency_failed["provider_calls"] == 2
    assert dependency_failed["diagnostic"] == "mechanics_acknowledgement_dependency_invalid"


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


def test_structured_provider_schema_requires_parser_claim_shape_and_mechanics_kind():
    from llm.advisor_client import _structured_provider_schema

    schema = _structured_provider_schema(mechanics_grounding_required=True)
    claim = schema["properties"]["primary_reasons"]["items"]
    assert claim["required"] == ["kind", "claim"]
    assert "mechanics" in claim["properties"]["kind"]["enum"]
    assert schema["properties"]["alternatives"]["items"]["properties"]["reason"] == claim
    assert "mechanics_acknowledgements" in schema["required"]
    assert schema["properties"]["mechanics_acknowledgements"]["items"]["required"] == ["slot_index", "move", "mechanics_path", "status", "missing_inputs_path"]


def test_single_direct_mechanics_schema_constrains_the_machine_acknowledgement_link():
    from llm.advisor_client import _structured_provider_schema

    payload = _prepared(FIXTURES[0])["recommendation_request"]
    schema = _structured_provider_schema(mechanics_grounding_required=True, provider_payload=payload)
    properties = schema["properties"]["mechanics_acknowledgements"]["items"]["properties"]
    assert properties["slot_index"]["enum"] == [0]
    assert properties["move"]["enum"] == ["tackle"]
    assert properties["mechanics_path"]["enum"] == ["candidate_comparisons.0.mechanics_result"]
    assert properties["status"]["enum"] == ["known"]
