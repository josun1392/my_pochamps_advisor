import pytest

from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _request():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})


@pytest.mark.parametrize("key", ["raw_response", "raw-provider-response", "traceback", "stack_trace", "api_key", "apikey", "token", "access_token", "refresh-token", "authorization", "credential", "credentials", "provider_secret", "client_secret", "raw_prompt", "provider_model", "network_configuration", "damage_range", "candidate_comparisons", "opponent_move", "ability", "EV", "IV"])
def test_forbidden_content_is_recursively_rejected_without_echoing_values(key):
    payload = {"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [{"nested": {key: "private-value"}}], "alternatives": []}
    result = parse_recommendation_response(request=_request(), response_payload=payload)
    assert result["errors"] == ["forbidden_response_content"] and "private-value" not in str(result)
