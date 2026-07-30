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
        mechanics_acknowledgements.append({"slot_index": row["slot_index"], "move": row["move"], "mechanics_path": path, "status": mechanics["status"], "missing_inputs_path": f"{path}.missing_inputs" if mechanics["status"] == "insufficient_context" else None})
        ranking_acknowledgements.append({"slot_index": row["slot_index"], "move": row["move"], **row["mechanics_comparison"]})
    grounding = {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [], "evidence_only": [], "conflicts": [], "conditional_dependencies": [{"path": acknowledgement["missing_inputs_path"]} for acknowledgement in mechanics_acknowledgements if acknowledgement["missing_inputs_path"] is not None]}
    selected_index = rows.index(winner)
    return {"recommendation_status": "resolved", "recommended_move": winner["move"], "recommended_slot_index": winner["slot_index"], "primary_reasons": [{"kind": "mechanics", "claim": "deterministic mechanics evidence", "mechanics_path": f"candidate_comparisons.{selected_index}.mechanics_result", "numeric_scope": "damage_range"}], "risks": [], "alternatives": [], "grounding": grounding, "mechanics_acknowledgements": mechanics_acknowledgements, "ranking_acknowledgements": ranking_acknowledgements}


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


def test_schema_requires_value_free_multi_move_ranking_acknowledgements():
    from llm.advisor_client import _structured_provider_schema

    payload = _prepared(FIXTURES[0])["recommendation_request"]
    schema = _structured_provider_schema(mechanics_grounding_required=True, ranking_acknowledgement_required=True, provider_payload=payload)
    item = schema["properties"]["ranking_acknowledgements"]["items"]
    assert "ranking_acknowledgements" in schema["required"]
    assert item["required"] == ["slot_index", "move", "comparison_status", "rank", "comparison_reason"]
    assert set(item["properties"]) == {"slot_index", "move", "comparison_status", "rank", "comparison_reason"}
    claim = schema["properties"]["primary_reasons"]["items"]
    assert "nullable" not in claim["properties"]["mechanics_path"]
    assert "nullable" not in claim["properties"]["numeric_scope"]
    assert "Use no digits in claim" in claim["properties"]["claim"]["description"]


def test_default_and_invalid_actual_paths_do_not_invoke_fake_provider():
    calls = []
    assert run_smoke(actual=False, provider_call=lambda _: calls.append(True))["provider_calls"] == 0
    invalid = run_smoke(actual=True, model="wrong", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=lambda _: calls.append(True))
    unavailable = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: False, provider_call=lambda _: calls.append(True))
    assert invalid["exit_code"] == EXIT["usage"] and unavailable["exit_code"] == EXIT["credential"]
    assert calls == []
