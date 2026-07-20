from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _candidate(status="partial", availability="partially_evaluable"):
    return {"slot_index": 0, "move": "protect", "status": status, "availability": availability, "damage": {"status": "not_applicable"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}


def _request(candidates):
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})


def test_valid_insufficient_context_and_no_usable_candidate_responses():
    insufficient = parse_recommendation_response(request=_request([_candidate()]), response_payload={"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [{"kind": "partial_context", "claim": "missing_context"}], "risks": [], "alternatives": []})
    no_usable = parse_recommendation_response(request=_request([_candidate("unavailable", "unavailable")]), response_payload={"recommendation_status": "no_usable_candidate", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": []})
    assert insufficient["status"] == "insufficient_context" and no_usable["status"] == "no_usable_candidate"
    no_candidates = parse_recommendation_response(request=_request([]), response_payload={"recommendation_status": "no_usable_candidate", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": []})
    assert no_candidates["status"] == "no_usable_candidate"


def test_resolved_response_on_non_ready_request_and_missing_slot_are_rejected():
    payload = {"recommendation_status": "resolved", "recommended_move": "protect", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []}
    assert parse_recommendation_response(request=_request([]), response_payload=payload)["status"] == "validation_failed"
    payload["recommended_slot_index"] = None
    assert parse_recommendation_response(request=_request([_candidate()]), response_payload=payload)["errors"] == ["missing_recommended_candidate"]
    rejected = parse_recommendation_response(request=_request([_candidate()]), response_payload={"recommendation_status": "validation_failed", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": []})
    assert rejected["errors"] == ["unsupported_recommendation_status"]
