import pytest

from llm.advisor_candidate_contract import build_recommendation_request, parse_recommendation_response


def _request(**fields):
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": [], **fields}
    return build_recommendation_request(evidence_bundle={"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []})


def _response(reason):
    return {"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [reason], "risks": [], "alternatives": []}


@pytest.mark.parametrize(("reason", "fields"), [
    ({"kind": "damage", "claim": "resolved_damage_available"}, {}),
    ({"kind": "ko", "claim": "ko_available"}, {"damage": {"status": "resolved", "ko": "possible"}}),
    ({"kind": "hit_chance", "claim": "hit_available"}, {"hit_chance": {"status": "resolved"}}),
    ({"kind": "hit_chance", "claim": "accuracy_available"}, {"accuracy_evidence": {"status": "known_accuracy"}}),
    ({"kind": "move_order", "claim": "order_available"}, {"move_order": {"status": "resolved"}}),
    ({"kind": "move_order", "claim": "action_order_available"}, {"action_order": {"status": "acts_first"}}),
    ({"kind": "dynamic_mechanic", "claim": "dynamic_available"}, {"dynamic_move": {"status": "resolved"}}),
    ({"kind": "self_effect", "claim": "effect_available"}, {"self_effects": [{"kind": "heal"}]}),
])
def test_claims_require_emitted_deterministic_evidence(reason, fields):
    assert parse_recommendation_response(request=_request(**fields), response_payload=_response(reason))["status"] == "resolved"


@pytest.mark.parametrize(("reason", "fields"), [
    ({"kind": "damage", "claim": "x"}, {"damage": {"status": "unavailable"}}),
    ({"kind": "ko", "claim": "x"}, {}), ({"kind": "hit_chance", "claim": "x"}, {}),
    ({"kind": "move_order", "claim": "x"}, {}), ({"kind": "dynamic_mechanic", "claim": "x"}, {}),
    ({"kind": "self_effect", "claim": "x"}, {}), ({"kind": "partial_context", "claim": "missing evidence"}, {}),
    ({"kind": "unsupported", "claim": "x"}, {}),
])
def test_missing_or_unsupported_claim_evidence_is_rejected(reason, fields):
    assert parse_recommendation_response(request=_request(**fields), response_payload=_response(reason))["status"] == "validation_failed"


def test_nested_secret_and_raw_response_fields_are_rejected():
    for key in ("raw_response", "nested"):
        payload = _response({"kind": "damage", "claim": "x"})
        if key == "raw_response": payload[key] = "never-return"
        else: payload["risks"] = [{"kind": "partial_context", "claim": "x", "nested": {"API-Key": "never-return"}}]
        result = parse_recommendation_response(request=_request(), response_payload=payload)
        assert result["errors"] == ["forbidden_response_content"] and "never-return" not in str(result)
