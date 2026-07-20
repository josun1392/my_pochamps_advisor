import json

import llm.advisor_client as client


PAYLOAD = {key: value for key, value in zip(("request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails"), ("v", {}, [], [], [], [], {}))}


class _Response:
    ok = True
    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"recommendation_status": "insufficient_context", "recommended_move": None, "recommended_slot_index": None, "primary_reasons": [], "risks": [], "alternatives": []})}]}}], "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2, "cachedContentTokenCount": 3}}


def test_structured_call_uses_one_json_schema_request_and_returns_usage(monkeypatch):
    seen = []
    monkeypatch.setattr(client.os, "environ", {"GEMINI_API_KEY": "present"})
    monkeypatch.setattr(client.requests, "post", lambda *args, **kwargs: seen.append((args, kwargs)) or _Response())
    decoded, usage = client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="model")
    assert len(seen) == 1 and set(seen[0][1]["json"]["generationConfig"]) == {"responseMimeType", "responseSchema"}
    assert decoded["recommendation_status"] == "insufficient_context" and usage["input_tokens"] == 1


def test_structured_call_rejects_markdown_and_never_falls_back(monkeypatch):
    class Markdown(_Response):
        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "```json {}"}]}}]}
    monkeypatch.setattr(client.os, "environ", {"GEMINI_API_KEY": "present"})
    monkeypatch.setattr(client.requests, "post", lambda *args, **kwargs: Markdown())
    try:
        client.call_structured_recommendation_provider(provider_payload=PAYLOAD, model="model")
    except client.StructuredProviderError as error:
        assert error.code == "provider_response_malformed"
    else:
        raise AssertionError("structured markdown must be rejected")
