from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _ready_request():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})


def test_completion_boundary_reuses_offline_parser_without_provider_or_ui_state():
    result = parse_recommendation_response(request=_ready_request(), response_payload={"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []})
    assert result == {"status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "errors": []}


def test_non_ready_cycle_contract_blocks_a_response_completion_boundary():
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [], "known_limitations": []})
    result = parse_recommendation_response(request=request, response_payload={"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []})
    assert result["status"] == "validation_failed" and result["errors"] == ["recommended_candidate_not_selectable"]
