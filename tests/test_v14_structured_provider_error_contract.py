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


def test_structured_provider_classifies_http_and_request_failures_without_raw_detail(monkeypatch):
    monkeypatch.setattr(client.os, "environ", {"GEMINI_API_KEY": "present"})

    class Failure:
        ok = False
        def __init__(self, status_code): self.status_code = status_code

    for status_code, expected in ((400, "provider_invalid_request"), (401, "provider_authentication_failure"), (403, "provider_permission_failure"), (404, "provider_model_not_found"), (429, "provider_quota_or_rate_limit"), (503, "provider_service_unavailable")):
        monkeypatch.setattr(client.requests, "post", lambda *args, _status=status_code, **kwargs: Failure(_status))
        try:
            client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")
        except client.StructuredProviderError as error:
            assert error.code == expected and "raw" not in str(error)
        else:
            raise AssertionError("non-success HTTP response must fail")

    monkeypatch.setattr(client.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(client.requests.ConnectionError("raw network detail")))
    try:
        client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")
    except client.StructuredProviderError as error:
        assert error.code == "provider_network_failure" and "raw" not in str(error)


def test_structured_provider_reports_missing_credential_as_authentication_failure(monkeypatch):
    monkeypatch.setattr(client.os, "environ", {})
    try:
        client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="m")
    except client.StructuredProviderError as error:
        assert error.code == "provider_authentication_failure"
