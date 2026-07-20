import pytest

from llm.advisor_candidate_contract import adapt_provider_recommendation_response


def _response(status="resolved"):
    return {"recommendation_status": status, "recommended_move": "move" if status == "resolved" else None, "recommended_slot_index": 0 if status == "resolved" else None, "primary_reasons": [], "risks": [], "alternatives": []}


@pytest.mark.parametrize("status", ["resolved", "insufficient_context", "no_usable_candidate"])
def test_allowed_structured_responses_are_independently_copied(status):
    response = _response(status); adapted = adapt_provider_recommendation_response(provider_response=response); response["risks"].append("mutated")
    assert adapted["recommendation_status"] == status and adapted["risks"] == []


@pytest.mark.parametrize("response", [_response("validation_failed"), "freeform", b"bytes", {**_response(), "usage": {}}, {"recommendation_status": "resolved"}])
def test_invalid_status_freeform_provider_objects_and_metadata_are_rejected(response):
    assert adapt_provider_recommendation_response(provider_response=response)["status"] == "provider_response_validation_failed"
