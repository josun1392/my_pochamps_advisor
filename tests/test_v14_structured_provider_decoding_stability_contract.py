import json
import pytest

import llm.advisor_client as client
from tests.test_v14_structured_provider_call_contract import PAYLOAD


class Response:
    ok = True
    def __init__(self, body): self.body = body
    def json(self): return self.body


def _call(monkeypatch, body):
    monkeypatch.setattr(client.os, "environ", {"GEMINI_API_KEY": "present"})
    monkeypatch.setattr(client.requests, "post", lambda *a, **k: Response(body))
    return client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")


@pytest.mark.parametrize("body,code", [
    ({"candidates": []}, "provider_response_missing"),
    ({"candidates": [{"content": {"parts": []}}]}, "provider_response_missing"),
    ({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}, "provider_response_malformed"),
    ({"candidates": [{"content": {"parts": [{"text": "```json {}"}]}}]}, "provider_response_malformed"),
    ({"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []}, "provider_safety_blocked"),
])
def test_decoder_classifies_missing_fenced_array_and_safety_without_body(body, code, monkeypatch):
    with pytest.raises(client.StructuredProviderError, match=code): _call(monkeypatch, body)


def test_decoder_rejects_unknown_response_field_before_runtime(monkeypatch):
    decoded = {"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": [], "raw_response": "x"}
    with pytest.raises(client.StructuredProviderError, match="provider_response_malformed"):
        _call(monkeypatch, {"candidates": [{"content": {"parts": [{"text": json.dumps(decoded)}]}}]})
