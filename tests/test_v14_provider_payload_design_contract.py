from llm.advisor_candidate_contract import build_recommendation_request, serialize_recommendation_request


OUTBOUND_KEYS = {"request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails"}


def test_future_outbound_payload_is_ready_request_allowlist_and_serializable():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})
    outbound = {key: request[key] for key in OUTBOUND_KEYS}
    assert set(outbound) == OUTBOUND_KEYS and serialize_recommendation_request(outbound) == outbound
    assert not ({"api_key", "authorization", "provider_model", "raw_response", "token_usage"} & set(outbound))


def test_design_requires_ready_cycle_before_provider_boundary():
    prepared = {"status": "no_selectable_candidates", "recommendation_request": None}
    assert prepared["status"] != "ready" and prepared["recommendation_request"] is None
