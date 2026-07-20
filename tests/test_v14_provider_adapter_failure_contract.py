from llm.advisor_candidate_contract import build_recommendation_request, run_offline_recommendation_provider_adapter


def _prepared():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    evidence = {"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []}
    return {"status": "ready", "candidates": [candidate], "evidence_bundle": evidence, "recommendation_request": build_recommendation_request(evidence_bundle=evidence), "errors": []}


def test_fake_provider_exception_and_malformed_response_are_sanitized_without_raw_retention():
    prepared = _prepared()
    unavailable = run_offline_recommendation_provider_adapter(prepared_cycle=prepared, fake_provider=lambda _: (_ for _ in ()).throw(RuntimeError("secret")))
    malformed = run_offline_recommendation_provider_adapter(prepared_cycle=prepared, fake_provider=lambda _: "raw secret")
    invalid = run_offline_recommendation_provider_adapter(prepared_cycle=prepared, fake_provider=lambda _: {"recommendation_status": "validation_failed"})
    assert unavailable["status"] == "provider_unavailable" and "secret" not in str(unavailable)
    assert malformed["status"] == "provider_response_malformed" and malformed["response_payload"] is None
    assert invalid["status"] == "provider_response_validation_failed" and invalid["prepared_cycle"]["evidence_bundle"] == prepared["evidence_bundle"]
