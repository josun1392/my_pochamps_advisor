import llm.advisor_client as client
from tests.test_v14_structured_provider_call_contract import PAYLOAD


def test_structured_provider_sanitizes_timeout_and_malformed_json(monkeypatch):
    monkeypatch.setattr(client.os, "environ", {"GEMINI_API_KEY": "present"})
    monkeypatch.setattr(client.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(client.requests.Timeout()))
    try:
        client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")
    except client.StructuredProviderError as error:
        assert error.code == "provider_timeout" and "Timeout" not in str(error)
    class Bad:
        ok = True
        def json(self): raise ValueError("raw")
    monkeypatch.setattr(client.requests, "post", lambda *args, **kwargs: Bad())
    try:
        client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")
    except client.StructuredProviderError as error:
        assert error.code == "provider_structured_decode_failed"
    else:
        raise AssertionError("bad JSON must fail")


def test_structured_provider_maps_safety_and_missing_content_without_body_detail(monkeypatch):
    monkeypatch.setattr(client.os, "environ", {"GEMINI_API_KEY": "present"})
    class Safety:
        ok = True
        def json(self): return {"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []}
    monkeypatch.setattr(client.requests, "post", lambda *args, **kwargs: Safety())
    try:
        client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")
    except client.StructuredProviderError as error:
        assert error.code == "provider_safety_blocked"
