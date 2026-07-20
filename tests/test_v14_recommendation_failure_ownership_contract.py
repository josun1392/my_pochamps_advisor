from copy import deepcopy

from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def test_provider_and_response_failure_design_preserves_deterministic_evidence_and_hides_raw_payload():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})
    before = deepcopy(request)
    result = parse_recommendation_response(request=request, response_payload={"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [{"raw_response": "private"}], "alternatives": []})
    assert result["status"] == "validation_failed" and "private" not in str(result)
    assert request == before


def test_design_has_no_ranking_turn_engine_or_ui_recommendation_on_failure():
    failure = {"status": "candidate_evaluation_failed", "errors": ["move_metadata_unavailable"]}
    assert "ranking" not in failure and "turn_engine" not in failure and "recommendation" not in failure
