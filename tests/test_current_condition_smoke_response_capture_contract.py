from __future__ import annotations

import json
from dataclasses import asdict

import pytest

import llm.advisor_client as advisor_client
import ui.main_window as main_window_module
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload
from ui.main_window import LLMAdviceWorker


_SENTINEL_RESPONSE = (
    "SELF_BURN_CURRENT OPPONENT_UNKNOWN FOCUS_SASH_OBSERVED "
    "NO_RESOLVED_OUTCOME"
)


def _fixture_battle_input() -> dict:
    battle_input = _opponent_move_ui_advice_flow_payload()
    battle_input["current_condition_confirmations"] = [
        {
            "side": "self",
            "condition_type": "burn",
            "status": "user_confirmed",
            "source": "user_confirmed_current_condition",
        },
        {
            "side": "opponent",
            "condition_type": "unknown",
            "status": "user_confirmed",
            "source": "user_confirmed_current_condition",
        },
    ]
    battle_input["item_event_confirmations"] = [
        {
            "side": "opponent",
            "item": "focus-sash",
            "event_type": "item_activation_observed",
            "status": "user_confirmed",
            "source": "explicit_user_event_confirmation",
        }
    ]
    return battle_input


def _prompt_payload(prompt: str) -> dict:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def test_smoke_capture_preserves_fake_provider_response_for_evaluator_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_prompts: list[str] = []
    evaluator_inputs: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v12-63-capture"
        captured_prompts.append(prompt)
        return _SENTINEL_RESPONSE, {"input_tokens": 101, "output_tokens": 11, "cached_tokens": 0}

    def fake_log_advisor_call(**kwargs: object) -> dict[str, object]:
        return {"mocked": True}

    def evaluator(response: str) -> tuple[str, str]:
        evaluator_inputs.append(response)
        assert response == _SENTINEL_RESPONSE
        return "pass", "Condition and observed event anchors were received."

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", fake_log_advisor_call)

    capture, usage, summary = advisor_client.run_ui_selected_advice_with_sanitized_smoke_capture(
        _fixture_battle_input(),
        evaluator,
        model="offline-v12-63-capture",
        enable_battle_state_context=True,
    )

    assert evaluator_inputs == [_SENTINEL_RESPONSE]
    assert usage == {"input_tokens": 101, "output_tokens": 11, "cached_tokens": 0}
    assert summary == {"mocked": True}
    assert capture.provider_status == "provider_success"
    assert capture.semantic_status == "pass"
    assert capture.sanitized_summary == "Condition and observed event anchors were received."
    assert _SENTINEL_RESPONSE not in asdict(capture).values()

    payload = _prompt_payload(captured_prompts[0])
    assert payload["condition_context"]["current_conditions"][0]["condition_type"] == "burn"
    assert payload["condition_context"]["current_conditions"][1]["condition_type"] == "unknown"
    assert payload["item_event_context"]["observed_events"][0]["item"] == "focus-sash"


def test_evaluator_failure_is_provider_success_with_response_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        advisor_client,
        "call_gemini",
        lambda prompt, model: (_SENTINEL_RESPONSE, {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}),
    )
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    def failing_evaluator(response: str) -> tuple[str, str]:
        assert response == _SENTINEL_RESPONSE
        raise RuntimeError("offline evaluator failure")

    capture, _, _ = advisor_client.run_ui_selected_advice_with_sanitized_smoke_capture(
        _fixture_battle_input(),
        failing_evaluator,
        model="offline-v12-63-capture",
        enable_battle_state_context=True,
    )

    assert capture.provider_status == "provider_success"
    assert capture.semantic_status == "response_unavailable"
    assert _SENTINEL_RESPONSE not in capture.sanitized_summary


def test_provider_failure_remains_distinct_from_semantic_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_provider(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        raise RuntimeError("offline provider failure")

    monkeypatch.setattr(advisor_client, "call_gemini", failing_provider)

    with pytest.raises(RuntimeError, match="offline provider failure"):
        advisor_client.run_ui_selected_advice_with_sanitized_smoke_capture(
            _fixture_battle_input(),
            lambda response: ("pass", "unreachable"),
            model="offline-v12-63-capture",
            enable_battle_state_context=True,
        )


def test_capture_rejects_unknown_semantic_status_without_persisting_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        advisor_client,
        "call_gemini",
        lambda prompt, model: (_SENTINEL_RESPONSE, {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}),
    )
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    with pytest.raises(ValueError, match="unsupported semantic status"):
        advisor_client.run_ui_selected_advice_with_sanitized_smoke_capture(
            _fixture_battle_input(),
            lambda response: ("raw_response", response),
            model="offline-v12-63-capture",
            enable_battle_state_context=True,
        )


def test_capture_rejects_a_summary_that_contains_the_full_provider_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        advisor_client,
        "call_gemini",
        lambda prompt, model: (_SENTINEL_RESPONSE, {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}),
    )
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    with pytest.raises(ValueError, match="must not contain the full provider response"):
        advisor_client.run_ui_selected_advice_with_sanitized_smoke_capture(
            _fixture_battle_input(),
            lambda response: ("pass", response),
            model="offline-v12-63-capture",
            enable_battle_state_context=True,
        )


def test_worker_finished_signal_preserves_recommendation_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_window_module,
        "run_ui_selected_advice",
        lambda *args, **kwargs: (_SENTINEL_RESPONSE, {"input_tokens": 1}, {"mocked": True}),
    )
    worker = LLMAdviceWorker(_fixture_battle_input(), enable_battle_state_context=True)
    received: list[tuple[str, dict]] = []
    worker.finished.connect(lambda recommendation, payload: received.append((recommendation, payload)))

    worker.run()

    assert received == [
        (_SENTINEL_RESPONSE, {"usage": {"input_tokens": 1}, "summary": {"mocked": True}})
    ]
