from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _request():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved", "ko": "possible"}, "hit_chance": {"status": "resolved"}, "move_order": {"status": "resolved"}, "dynamic_move": {"status": "resolved"}, "self_effects": [{"kind": "heal"}], "warnings": ["w"], "unavailable_reasons": ["r"]}
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {"x": [1]}, "candidates": [candidate], "known_limitations": ["limited"]})


def test_parser_deep_copies_response_and_never_mutates_request_evidence():
    request = _request(); request_before = deepcopy(request)
    payload = {"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [{"kind": "damage", "claim": "resolved_damage_available"}], "risks": [], "alternatives": []}
    result = parse_recommendation_response(request=request, response_payload=payload)
    payload["primary_reasons"][0]["claim"] = "mutated"; payload["risks"].append({"kind": "partial_context", "claim": "x"})
    assert result["primary_reasons"] == [{"kind": "damage", "claim": "resolved_damage_available"}] and result["risks"] == []
    assert request == request_before
