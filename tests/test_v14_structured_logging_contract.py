import inspect

import llm.advisor_client as client
from llm.advisor_client import run_structured_ui_recommendation


def test_structured_runtime_returns_usage_separately_without_logging_payload_or_response():
    source = inspect.getsource(run_structured_ui_recommendation)
    assert '"usage"' in source and "TokenLogger" not in source and "raw_response" not in source


def test_structured_path_has_no_legacy_provider_fallback_or_retry():
    source = inspect.getsource(run_structured_ui_recommendation)
    assert "run_ui_selected_advice" not in source and "call_gemini" not in source


def test_structured_usage_logging_uses_only_usage_and_survives_logger_failure(monkeypatch):
    seen = {}
    class Logger:
        def log_call(self, **kwargs): seen.update(kwargs)
    monkeypatch.setattr(client, "TokenLogger", Logger)
    summary = client._log_structured_recommendation_usage(model="m", usage={"input_tokens": 1, "output_tokens": 2, "cached_tokens": 3}, status="resolved")
    assert summary["logging_status"] == "recorded" and seen["tool_name"] == "structured_recommendation"
    monkeypatch.setattr(client, "TokenLogger", lambda: (_ for _ in ()).throw(RuntimeError("secret")))
    assert client._log_structured_recommendation_usage(model="m", usage={}, status="resolved")["logging_status"] == "failed"
