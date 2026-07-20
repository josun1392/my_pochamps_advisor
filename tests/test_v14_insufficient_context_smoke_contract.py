from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def test_sanitized_insufficient_context_shape_reproduces_invalid_claim_without_a_pair():
    candidate = {"slot_index": 0, "move": "generic-move", "status": "partial", "availability": "partially_evaluable", "damage": {"status": "unavailable", "reason": "deterministic_damage_unavailable"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": ["deterministic_damage_unavailable"]}
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": ["limited"]})
    response = {"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [{"kind": "unsupported", "claim": "sanitized"}], "risks": [], "alternatives": []}
    parsed = parse_recommendation_response(request=request, response_payload=response)
    assert parsed["status"] == "validation_failed" and parsed["errors"] == ["invalid_claim"]
    assert parsed["recommended_move"] is None and parsed["recommended_slot_index"] is None
