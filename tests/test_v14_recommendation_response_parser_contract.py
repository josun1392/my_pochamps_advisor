from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _request():
    candidate = {"slot_index": 0, "move": "flamethrower", "status": "resolved", "availability": "usable", "damage": {"status": "resolved", "minimum": 10, "maximum": 12, "ko": "possible"}, "hit_chance": {"status": "resolved"}, "move_order": {"status": "resolved"}, "dynamic_move": {"status": "resolved"}, "self_effects": [{"kind": "direct_healing"}], "warnings": [], "unavailable_reasons": []}
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})


def test_valid_resolved_response_is_pure_and_preserves_request_evidence():
    request = _request(); before = deepcopy(request)
    result = parse_recommendation_response(request=request, response_payload={"recommendation_status": "resolved", "recommended_move": "flamethrower", "recommended_slot_index": 0, "primary_reasons": [{"kind": "damage", "claim": "resolved_damage_available"}], "risks": [], "alternatives": []})
    assert result["status"] == "resolved" and result["errors"] == []
    assert request == before


def test_parser_failure_is_sanitized_without_payload_values():
    result = parse_recommendation_response(request=_request(), response_payload={"recommendation_status": "resolved", "recommended_move": "secret-value", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []})
    assert result["status"] == "validation_failed" and result["errors"] == ["recommended_candidate_not_selectable"]
    assert "secret-value" not in str(result)
