from copy import deepcopy

from scripts.run_sanitized_multi_move_mechanics_smoke import EXIT, FIXTURES, _prepared, run_smoke


def _response(payload, *, selected=None):
    rows = payload["candidate_comparisons"]
    winner = next(row for row in rows if row["mechanics_comparison"]["rank"] == 1)
    if selected is not None:
        winner = next(row for row in rows if (row["move"], row["slot_index"]) == selected)
    mechanics_acknowledgements = []
    ranking_acknowledgements = []
    for index, row in enumerate(rows):
        mechanics = row["mechanics_result"]
        path = f"candidate_comparisons.{index}.mechanics_result"
        mechanics_acknowledgements.append({"slot_index": row["slot_index"], "move": row["move"], "mechanics_path": path, "status": mechanics["status"], "missing_inputs_path": None})
        ranking_acknowledgements.append({"slot_index": row["slot_index"], "move": row["move"], **row["mechanics_comparison"]})
    grounding = {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [], "evidence_only": [], "conflicts": [], "conditional_dependencies": [{"path": acknowledgement["missing_inputs_path"]} for acknowledgement in mechanics_acknowledgements if acknowledgement["missing_inputs_path"] is not None]}
    return {"recommendation_status": "resolved", "recommended_move": winner["move"], "recommended_slot_index": winner["slot_index"], "primary_reasons": [{"kind": "mechanics", "claim": "deterministic mechanics evidence"}], "risks": [], "alternatives": [], "grounding": grounding, "mechanics_acknowledgements": mechanics_acknowledgements, "ranking_acknowledgements": ranking_acknowledgements}


def test_three_fixture_fake_provider_requires_rank_one_selection_and_exact_acknowledgements():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"]
    assert result["provider_calls"] == 3


def test_fixture_preparation_exercises_clear_winner_mixed_availability_and_stable_tie():
    clear, mixed, tie = (_prepared(fixture_id)["recommendation_request"]["candidate_comparisons"] for fixture_id in FIXTURES)
    assert [row["mechanics_comparison"]["rank"] for row in clear] == [2, 1]
    assert [row["mechanics_comparison"]["comparison_status"] for row in mixed] == ["rankable", "insufficient_context", "unsupported_mechanic"]
    assert [row["mechanics_comparison"]["rank"] for row in tie] == [1, 2]


def test_missing_or_mutated_ranking_acknowledgement_is_a_bounded_semantic_failure():
    def missing(payload):
        response = _response(payload)
        del response["ranking_acknowledgements"]
        return response

    failed = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=missing)
    assert failed["exit_code"] == EXIT["semantic"]
    assert failed["diagnostic"] == "ranking_acknowledgement_missing"
    assert failed["provider_calls"] == 1

    def mutated(payload):
        response = _response(payload)
        response["ranking_acknowledgements"][0]["rank"] = 1
        return response

    mutated_result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=mutated)
    assert mutated_result["exit_code"] == EXIT["semantic"]
    assert mutated_result["diagnostic"] == "ranking_acknowledgement_value_invalid"


def test_provider_cannot_select_a_non_rank_one_candidate_even_with_valid_acknowledgements():
    def lower_rank(payload):
        return _response(payload, selected=("tackle", 0))

    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=lower_rank)
    assert result["exit_code"] == EXIT["semantic"]
    assert result["diagnostic"] == "ranking_selection_mismatch"


def test_multi_move_claims_are_value_free_and_numeric_mechanics_are_rejected():
    from llm.advisor_candidate_contract import complete_recommendation_cycle

    prepared = _prepared(FIXTURES[0])
    response = _response(prepared["recommendation_request"])
    assert complete_recommendation_cycle(prepared_cycle=prepared, response_payload=response)["status"] == "resolved"

    for claim in ("50 damage", "20 percent", "0.5 KO probability"):
        numeric = _response(prepared["recommendation_request"])
        numeric["primary_reasons"][0]["claim"] = claim
        assert complete_recommendation_cycle(prepared_cycle=prepared, response_payload=numeric)["errors"] == ["multi_move_numeric_claim_forbidden"]

    referenced = _response(prepared["recommendation_request"])
    referenced["primary_reasons"][0]["mechanics_path"] = "candidate_comparisons.1.mechanics_result"
    assert complete_recommendation_cycle(prepared_cycle=prepared, response_payload=referenced)["errors"] == ["multi_move_claim_reference_forbidden"]


def test_multi_move_rejects_an_insufficient_candidate_reference_and_preserves_stable_tie():
    from llm.advisor_candidate_contract import complete_recommendation_cycle

    mixed = _prepared(FIXTURES[1])
    invalid = _response(mixed["recommendation_request"])
    invalid["primary_reasons"][0]["claim"] = "0 damage"
    assert complete_recommendation_cycle(prepared_cycle=mixed, response_payload=invalid)["errors"] == ["multi_move_numeric_claim_forbidden"]

    tie = _prepared(FIXTURES[2])
    accepted = complete_recommendation_cycle(prepared_cycle=tie, response_payload=_response(tie["recommendation_request"]))
    assert accepted["status"] == "resolved"
    assert (accepted["recommendation_result"]["recommended_move"], accepted["recommendation_result"]["recommended_slot_index"]) == ("tackle", 0)


def test_multi_move_allows_only_null_incomplete_dependency_copy_while_single_direct_stays_strict():
    from llm.advisor_candidate_contract import complete_recommendation_cycle

    mixed = _prepared(FIXTURES[1])
    accepted = complete_recommendation_cycle(prepared_cycle=mixed, response_payload=_response(mixed["recommendation_request"]))
    assert accepted["status"] == "resolved"

    malformed = _response(mixed["recommendation_request"])
    malformed["mechanics_acknowledgements"][1]["missing_inputs_path"] = "invalid"
    assert complete_recommendation_cycle(prepared_cycle=mixed, response_payload=malformed)["errors"] == ["mechanics_acknowledgement_dependency_invalid"]


def test_schema_requires_value_free_multi_move_ranking_acknowledgements():
    from llm.advisor_client import _structured_provider_schema

    payload = _prepared(FIXTURES[0])["recommendation_request"]
    schema = _structured_provider_schema(mechanics_grounding_required=True, ranking_acknowledgement_required=True, provider_payload=payload)
    item = schema["properties"]["ranking_acknowledgements"]["items"]
    assert "ranking_acknowledgements" in schema["required"]
    assert item["required"] == ["slot_index", "move", "comparison_status", "rank", "comparison_reason"]
    assert set(item["properties"]) == {"slot_index", "move", "comparison_status", "rank", "comparison_reason"}
    claim = schema["properties"]["primary_reasons"]["items"]
    assert set(claim["properties"]) == {"kind", "claim"}
    assert claim["required"] == ["kind", "claim"]
    assert claim["properties"]["claim"]["enum"] == ["deterministic ranking evidence", "deterministic comparison supports the selected action", "selected action follows deterministic ranking"]
    dependency = schema["properties"]["mechanics_acknowledgements"]["items"]["properties"]["missing_inputs_path"]["description"]
    assert "always use null" in dependency


def test_multi_move_keeps_native_numeric_evidence_in_the_deterministic_request_and_result():
    prepared = _prepared(FIXTURES[0])
    comparison = prepared["recommendation_request"]["candidate_comparisons"][1]
    mechanics = comparison["mechanics_result"]
    assert set(("damage_range", "damage_percent_range", "ko_result")) <= set(mechanics)
    accepted = __import__("llm.advisor_candidate_contract", fromlist=["complete_recommendation_cycle"]).complete_recommendation_cycle(prepared_cycle=prepared, response_payload=_response(prepared["recommendation_request"]))
    assert accepted["candidates"][1]["mechanics_result"] == mechanics


def test_default_and_invalid_actual_paths_do_not_invoke_fake_provider():
    calls = []
    assert run_smoke(actual=False, provider_call=lambda _: calls.append(True))["provider_calls"] == 0
    invalid = run_smoke(actual=True, model="wrong", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=lambda _: calls.append(True))
    unavailable = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: False, provider_call=lambda _: calls.append(True))
    assert invalid["exit_code"] == EXIT["usage"] and unavailable["exit_code"] == EXIT["credential"]
    assert calls == []
