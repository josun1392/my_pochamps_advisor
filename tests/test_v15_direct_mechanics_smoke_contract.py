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

    class RateLimit(Exception):
        code = "provider_quota_or_rate_limit"

    rate_limited = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=lambda _: (_ for _ in ()).throw(RateLimit()))
    assert rate_limited["exit_code"] == EXIT["provider"]
    assert rate_limited["diagnostic"] == "provider_quota_or_rate_limit"

    class InvalidRequest(Exception):
        code = "provider_invalid_request"
        safe_context = {"http_status": 400, "api_status": "INVALID_ARGUMENT", "stage": "http_response", "component": "response_schema", "logical_field": "mechanics_acknowledgements", "reason": "schema_keyword_enum", "raw": "must-not-surface"}

    invalid_request = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=(FIXTURES[0],), max_calls=1, no_retry=True, credential_available=lambda: True, provider_call=lambda _: (_ for _ in ()).throw(InvalidRequest()))
    assert invalid_request["exit_code"] == EXIT["provider"]
    assert invalid_request["provider_diagnostic"] == {"http_status": 400, "api_status": "INVALID_ARGUMENT", "stage": "http_response", "component": "response_schema", "logical_field": "mechanics_acknowledgements", "reason": "schema_keyword_enum"}
    assert "raw" not in str(invalid_request["provider_diagnostic"])


def test_one_fixture_diagnostic_run_has_a_hard_one_call_limit():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=(FIXTURES[0],), max_calls=1, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"]
    assert result["provider_calls"] == 1


def test_known_mechanics_numeric_claim_requires_exact_native_scope_and_insufficient_blocks_it():
    import pytest
    from llm.advisor_candidate_contract import _validate_claim, complete_recommendation_cycle

    complete = _prepared(FIXTURES[0])
    accepted = complete_recommendation_cycle(prepared_cycle=complete, response_payload=_response(complete["recommendation_request"]))
    assert accepted["status"] == "resolved"

    mechanics = complete["recommendation_request"]["candidate_comparisons"][0]["mechanics_result"]
    numeric = _response(complete["recommendation_request"])
    numeric["primary_reasons"] = [{"kind": "mechanics", "claim": f"{mechanics['damage_range']['minimum']}-{mechanics['damage_range']['maximum']} damage", "mechanics_path": "candidate_comparisons.0.mechanics_result", "numeric_scope": "damage_range"}]
    assert complete_recommendation_cycle(prepared_cycle=complete, response_payload=numeric)["status"] == "resolved"

    for scope, values in (("damage_percent_range", mechanics["damage_percent_range"].values()), ("single_hit_probability", (mechanics["ko_result"]["single_hit_probability"],))):
        scoped = _response(complete["recommendation_request"])
        scoped["primary_reasons"] = [{"kind": "mechanics", "claim": "-".join(str(value) for value in values), "mechanics_path": "candidate_comparisons.0.mechanics_result", "numeric_scope": scope}]
        assert complete_recommendation_cycle(prepared_cycle=complete, response_payload=scoped)["status"] == "resolved"

    mismatch = _response(complete["recommendation_request"])
    mismatch["primary_reasons"] = [{"kind": "mechanics", "claim": "50 damage", "mechanics_path": "candidate_comparisons.0.mechanics_result", "numeric_scope": "damage_range"}]
    assert complete_recommendation_cycle(prepared_cycle=complete, response_payload=mismatch)["errors"] == ["mechanics_numeric_value_mismatch"]

    wrong_path = _response(complete["recommendation_request"])
    wrong_path["primary_reasons"] = [{"kind": "mechanics", "claim": f"{mechanics['damage_range']['minimum']}-{mechanics['damage_range']['maximum']} damage", "mechanics_path": "candidate_comparisons.1.mechanics_result", "numeric_scope": "damage_range"}]
    assert complete_recommendation_cycle(prepared_cycle=complete, response_payload=wrong_path)["errors"] == ["mechanics_numeric_scope_invalid"]

    incomplete = _prepared(FIXTURES[1])
    with pytest.raises(ValueError, match="mechanics_claim_on_insufficient_context"):
        _validate_claim({"kind": "mechanics", "claim": "deterministic mechanics"}, incomplete["candidates"][0])

    insufficient_numeric = _response(incomplete["recommendation_request"])
    insufficient_numeric["primary_reasons"] = [{"kind": "partial_context", "claim": "1-2 damage", "mechanics_path": "candidate_comparisons.0.mechanics_result", "numeric_scope": "damage_range"}]
    assert complete_recommendation_cycle(prepared_cycle=incomplete, response_payload=insufficient_numeric)["errors"] == ["mechanics_numeric_claim_on_insufficient_context"]


def test_structured_provider_schema_requires_parser_claim_shape_and_mechanics_kind():
    from llm.advisor_client import _structured_provider_schema

    schema = _structured_provider_schema(mechanics_grounding_required=True)
    claim = schema["properties"]["primary_reasons"]["items"]
    assert claim["required"] == ["kind", "claim"]
    assert "mechanics" in claim["properties"]["kind"]["enum"]
    assert set(("mechanics_path", "numeric_scope")) <= set(claim["properties"])
    assert schema["properties"]["alternatives"]["items"]["properties"]["reason"] == claim
    assert "mechanics_acknowledgements" in schema["required"]
    assert schema["properties"]["mechanics_acknowledgements"]["items"]["required"] == ["slot_index", "move", "mechanics_path", "status", "missing_inputs_path"]


def test_single_direct_mechanics_schema_keeps_dynamic_linkage_out_of_provider_enums():
    from llm.advisor_client import _structured_provider_schema

    payload = _prepared(FIXTURES[0])["recommendation_request"]
    schema = _structured_provider_schema(mechanics_grounding_required=True, provider_payload=payload)
    properties = schema["properties"]["mechanics_acknowledgements"]["items"]["properties"]
    assert "enum" not in properties["slot_index"]
    assert "enum" not in properties["move"]
    assert "enum" not in properties["mechanics_path"]
    assert properties["status"]["enum"] == ["known", "insufficient_context", "unsupported_mechanic"]
