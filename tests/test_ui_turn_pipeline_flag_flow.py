from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication

import llm.advisor_client as advisor_client
from tests.test_advisor_payload_contract import (
    _opponent_move_ui_advice_flow_payload,
    _turn_pipeline_advice_flow_payload,
)
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _prompt_payload(prompt: str) -> dict:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def test_limited_context_checkbox_defaults_off_and_toggle_does_not_call_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    emitted = 0
    provider_calls = 0

    def record_advice_request() -> None:
        nonlocal emitted
        emitted += 1

    def fail_on_provider_call(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        del prompt, model
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("checkbox toggle must not call provider")

    panel.advice_requested.connect(record_advice_request)
    monkeypatch.setattr(advisor_client, "call_gemini", fail_on_provider_call)

    assert panel.turn_pipeline_enabled() is False
    assert panel.turn_pipeline_checkbox.isChecked() is False

    panel.turn_pipeline_checkbox.setChecked(True)

    assert panel.turn_pipeline_enabled() is True
    assert emitted == 0
    assert provider_calls == 0

    panel.turn_pipeline_checkbox.setChecked(False)

    assert panel.turn_pipeline_enabled() is False
    assert emitted == 0
    assert provider_calls == 0


def test_limited_context_checkbox_off_and_on_offline_advice_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    payload = _opponent_move_ui_advice_flow_payload()
    captured_prompts: list[str] = []
    logged_usages: list[dict[str, int]] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v9-2"
        captured_prompts.append(prompt)
        response = (
            "Mocked offline advice. Candidate turn events, turn order, and "
            "opponent moves are limited context only; selected opponent move remains unknown."
        )
        return response, {"input_tokens": 40 + len(captured_prompts), "output_tokens": 7, "cached_tokens": 0}

    def fake_log_advisor_call(*, model: str, usage: dict[str, int], game_id: str) -> dict[str, object]:
        assert model == "offline-v9-2"
        assert game_id == "ui_selected_pokemon_v0_6"
        logged_usages.append(usage)
        return {"mocked": True, "logged": len(logged_usages)}

    def run_from_panel() -> tuple[str, dict[str, int], dict[str, object]]:
        enabled = panel.turn_pipeline_enabled()
        return advisor_client.run_ui_selected_advice(
            payload,
            model="offline-v9-2",
            enable_turn_pipeline=enabled,
            enable_turn_order_context=enabled,
            enable_opponent_move_context=enabled,
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", fake_log_advisor_call)

    off_response, off_usage, off_summary = run_from_panel()

    panel.turn_pipeline_checkbox.setChecked(True)
    on_response, on_usage, on_summary = run_from_panel()

    assert len(captured_prompts) == 2
    assert len(logged_usages) == 2
    assert "Mocked offline advice" in off_response
    assert "Mocked offline advice" in on_response
    assert off_usage == {"input_tokens": 41, "output_tokens": 7, "cached_tokens": 0}
    assert on_usage == {"input_tokens": 42, "output_tokens": 7, "cached_tokens": 0}
    assert off_summary == {"mocked": True, "logged": 1}
    assert on_summary == {"mocked": True, "logged": 2}

    off_prompt, on_prompt = captured_prompts
    off_payload = _prompt_payload(off_prompt)
    on_payload = _prompt_payload(on_prompt)

    assert "turn_pipeline" not in off_payload
    assert "turn_order_context" not in off_payload
    assert "opponent_move_context" not in off_payload
    assert "candidate events are not resolved outcomes" not in off_prompt
    assert "limited planning context, not a resolved move order" not in off_prompt
    assert "If opponent_move_context is present" not in off_prompt

    assert on_payload["turn_pipeline"]["simulated"] == "limited"
    assert on_payload["turn_order_context"]["kind"] == "deterministic_turn_order_context"
    assert on_payload["opponent_move_context"]["kind"] == "opponent_move_context"

    context = on_payload["opponent_move_context"]
    assert context["known_opponent_moves"] == []
    assert context["selected_opponent_move"] == {"status": "unknown"}

    candidates = context["candidate_moves"]
    assert {candidate["move_id"] for candidate in candidates} == {"thunderbolt", "quick-attack"}
    assert next(candidate for candidate in candidates if candidate["move_id"] == "thunderbolt")["source"] == "visible_ui"
    assert next(candidate for candidate in candidates if candidate["move_id"] == "quick-attack")[
        "source"
    ] == "champions_movepool"
    assert all(candidate["confirmed"] is False and candidate["selected"] is False for candidate in candidates)

    assert '"turn_pipeline"' in on_prompt
    assert '"turn_order_context"' in on_prompt
    assert '"opponent_move_context"' in on_prompt
    assert "candidate events are not resolved outcomes" in on_prompt
    assert "limited planning/debug summary only, not full turn simulation" in on_prompt
    assert "limited planning context, not a resolved move order" in on_prompt
    assert "If opponent_move_context is present" in on_prompt
    assert "Candidate moves are not confirmed selected moves" in on_prompt
    assert "Do not infer hidden movesets" in on_prompt


def test_limited_context_checkbox_on_omits_empty_opponent_move_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    panel.turn_pipeline_checkbox.setChecked(True)
    payload = _turn_pipeline_advice_flow_payload()
    captured_prompts: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v9-2-empty-opponent"
        captured_prompts.append(prompt)
        return "mocked empty opponent context flow", {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    enabled = panel.turn_pipeline_enabled()
    advisor_client.run_ui_selected_advice(
        payload,
        model="offline-v9-2-empty-opponent",
        enable_turn_pipeline=enabled,
        enable_turn_order_context=enabled,
        enable_opponent_move_context=enabled,
    )

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    prompt_payload = _prompt_payload(prompt)
    assert "turn_pipeline" in prompt_payload
    assert "turn_order_context" in prompt_payload
    assert "opponent_move_context" not in prompt_payload
    assert "If opponent_move_context is present" not in prompt
