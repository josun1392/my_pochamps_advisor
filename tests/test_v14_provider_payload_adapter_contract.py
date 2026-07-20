from copy import deepcopy
import math

from llm.advisor_candidate_contract import build_provider_recommendation_payload, build_recommendation_request


def _prepared():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    evidence = {"battle_snapshot_summary": {"x": [1]}, "candidates": [candidate], "known_limitations": []}
    return {"status": "ready", "candidates": [candidate], "evidence_bundle": evidence, "recommendation_request": build_recommendation_request(evidence_bundle=evidence), "errors": []}


def test_ready_cycle_produces_exact_seven_field_independent_payload_in_order():
    prepared = _prepared(); payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    prepared["recommendation_request"]["candidate_exact_set"][0]["move"] = "mutated"
    assert list(payload) == ["request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails"]
    assert payload["candidate_exact_set"] == [{"slot_index": 0, "move": "move"}] and "candidates" not in payload


def test_nonready_missing_invalid_and_forbidden_requests_are_sanitized():
    assert build_provider_recommendation_payload(prepared_cycle={"status": "no_candidates"}) == {"status": "prepared_cycle_not_ready", "errors": ["prepared_cycle_not_ready"]}
    assert build_provider_recommendation_payload(prepared_cycle={"status": "ready"}) == {"status": "provider_payload_validation_failed", "errors": ["provider_payload_validation_failed"]}
    prepared = _prepared(); prepared["recommendation_request"]["nested"] = {"API-Key": "secret"}
    assert build_provider_recommendation_payload(prepared_cycle=prepared)["status"] == "provider_payload_validation_failed"
    prepared = _prepared(); prepared["recommendation_request"]["known_limitations"] = [math.nan]
    assert build_provider_recommendation_payload(prepared_cycle=prepared)["status"] == "provider_payload_validation_failed"
