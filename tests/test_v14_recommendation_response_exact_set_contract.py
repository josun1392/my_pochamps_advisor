from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _request():
    candidates = []
    for slot in (0, 2):
        candidates.append({"slot_index": slot, "move": "flamethrower", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []})
    candidates.append({"slot_index": 1, "move": "missing", "status": "unavailable", "availability": "unavailable", "damage": {"status": "unavailable"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []})
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": []})


def _payload(move, slot):
    return {"recommendation_status": "resolved", "recommended_move": move, "recommended_slot_index": slot, "primary_reasons": [], "risks": [], "alternatives": []}


def test_duplicate_move_slots_require_the_exact_pair_and_unavailable_is_rejected():
    request = _request()
    assert parse_recommendation_response(request=request, response_payload=_payload("flamethrower", 2))["status"] == "resolved"
    assert parse_recommendation_response(request=request, response_payload=_payload("flamethrower", 3))["status"] == "validation_failed"
    assert parse_recommendation_response(request=request, response_payload=_payload("missing", 1))["status"] == "validation_failed"


def test_alternatives_require_distinct_selectable_exact_pairs_not_the_primary():
    request = _request(); payload = _payload("flamethrower", 0)
    payload["alternatives"] = [{"move": "flamethrower", "slot_index": 2, "reason": {"kind": "partial_context", "claim": "safer_under_uncertainty"}}]
    assert parse_recommendation_response(request=request, response_payload=payload)["status"] == "resolved"
    payload["alternatives"].append(payload["alternatives"][0].copy())
    assert parse_recommendation_response(request=request, response_payload=payload)["status"] == "validation_failed"
    payload["alternatives"] = [{"move": "flamethrower", "slot_index": 0, "reason": {"kind": "partial_context", "claim": "same"}}]
    assert parse_recommendation_response(request=request, response_payload=payload)["status"] == "validation_failed"
    payload["alternatives"] = [{"move": "flamethrower", "slot_index": 2}]
    assert parse_recommendation_response(request=request, response_payload=payload)["status"] == "validation_failed"
