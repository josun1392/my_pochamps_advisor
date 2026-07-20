from llm.advisor_candidate_contract import build_recommendation_request


def test_future_provider_adapter_input_is_immutable_approved_request_only():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})
    assert request["readiness"]["status"] == "ready"
    assert not ({"api_key", "provider_model", "raw_response", "network_configuration"} & set(request))


def test_provider_failure_design_keeps_prepared_evidence_and_blocks_raw_response_boundary():
    prepared = {"status": "ready", "candidates": [{"move": "move"}], "evidence_bundle": {"candidates": [{"move": "move"}]}, "recommendation_request": {"readiness": {"status": "ready"}}}
    provider_failure = {"status": "provider_failure", "errors": ["provider_unavailable"], "prepared_cycle": prepared}
    assert provider_failure["prepared_cycle"]["evidence_bundle"] == prepared["evidence_bundle"]
    assert "raw_response" not in provider_failure
