from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
from tests.test_advisor_payload_contract import (
    _opponent_move_ui_advice_flow_payload,
    _turn_pipeline_advice_flow_payload,
)
from ui.widgets.llm_advice_panel import LLMAdvicePanel, TURN_PIPELINE_HELP_TEXT, TURN_PIPELINE_STATUS_TEXT


def _prompt_payload(prompt: str) -> dict:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def test_limited_context_checkbox_copy_describes_combined_candidate_context() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()

    assert panel.turn_pipeline_checkbox.text() == "제한 컨텍스트 포함"
    assert panel.turn_pipeline_checkbox.toolTip() == TURN_PIPELINE_HELP_TEXT
    assert panel.turn_pipeline_status_label.text() == TURN_PIPELINE_STATUS_TEXT

    assert panel.turn_pipeline_checkbox.text() == "제한 컨텍스트 포함"
    assert panel.turn_pipeline_checkbox.isChecked() is False

    combined_copy = " ".join(
        (
            panel.turn_pipeline_checkbox.text(),
            panel.turn_pipeline_checkbox.toolTip(),
            panel.turn_pipeline_status_label.text(),
        )
    )
    for required_phrase in (
        "후보 이벤트",
        "선후공 보조 정보",
        "UI에 보이는 상대 기술 후보",
        "현재 포켓몬/HP 스냅샷",
        "확정 결과가 아니",
        "실제 선택 기술",
        "숨겨진 아이템/상태/랭크/필드",
        "턴 후 HP",
        "아이템 소모",
        "RNG",
        "스피드 타이",
        "Quick Claw 발동",
        "전체 턴 결과",
    ):
        assert required_phrase in combined_copy

    forbidden_phrases = (
        "상대가 사용할 기술",
        "상대 선택 기술",
        "확정 선후공",
        "확정 전투 결과",
        "확정 턴 결과입니다",
        "숨겨진 아이템일 가능성",
        "상태이상을 추론",
        "랭크 변화를 추론",
        "필드 상태를 추론",
        "턴 후 HP 확정",
        "아이템 소모 확정",
        "RNG 결과 확정",
        "스피드 타이 결과 확정",
        "Quick Claw 발동 확정",
        "전체 턴 결과 확정",
        "숨겨진 기술배치 추론",
    )
    for phrase in forbidden_phrases:
        assert phrase not in combined_copy


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
    provider_calls = 0

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        nonlocal provider_calls
        assert model == "offline-v9-2"
        provider_calls += 1
        captured_prompts.append(prompt)
        response = (
            "Mocked offline advice. Candidate turn events, turn order, and "
            "opponent moves are limited context only. Battle state is visible species and HP context only; "
            "selected opponent move and hidden battle state remain unknown."
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
            enable_battle_state_context=enabled,
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", fake_log_advisor_call)

    off_response, off_usage, off_summary = run_from_panel()

    panel.turn_pipeline_checkbox.setChecked(True)
    on_response, on_usage, on_summary = run_from_panel()

    assert len(captured_prompts) == 2
    assert len(logged_usages) == 2
    assert provider_calls == 2
    assert "Mocked offline advice" in off_response
    assert "Mocked offline advice" in on_response
    for response in (off_response, on_response):
        response_lower = response.lower()
        for forbidden_response_phrase in (
            "hidden item is confirmed",
            "evs are likely",
            "ivs are likely",
            "nature is likely",
            "post-turn hp will be",
            "item will be consumed",
            "rng resolved",
            "speed tie resolved",
            "quick claw activates",
            "full turn outcome",
        ):
            assert forbidden_response_phrase not in response_lower
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
    assert "battle_state_context" not in off_payload
    assert "candidate events are not resolved outcomes" not in off_prompt
    assert "limited planning context, not a resolved move order" not in off_prompt
    assert "If opponent_move_context is present" not in off_prompt
    assert "If battle_state_context is present" not in off_prompt
    assert "Unknown battle state fields must remain unknown" not in off_prompt

    assert on_payload["turn_pipeline"]["simulated"] == "limited"
    assert on_payload["turn_order_context"]["kind"] == "deterministic_turn_order_context"
    assert on_payload["opponent_move_context"]["kind"] == "opponent_move_context"
    assert on_payload["battle_state_context"]["kind"] == "battle_state_context"
    assert on_payload["battle_state_context"]["confidence"] == "limited"

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

    battle_state_context = on_payload["battle_state_context"]
    assert battle_state_context["self_active"]["species"] == {
        "source": "visible_ui",
        "name": on_payload["pokemon"]["my_active"]["name_en"],
    }
    assert battle_state_context["self_active"]["current_hp_percent"] == {
        "source": "visible_ui",
        "value": on_payload["pokemon"]["my_active"]["hp_percent"],
    }
    assert battle_state_context["opponent_active"]["species"] == {
        "source": "visible_ui",
        "name": on_payload["pokemon"]["opponent_active"]["name_en"],
    }
    assert battle_state_context["opponent_active"]["current_hp_percent"] == {
        "source": "visible_ui",
        "value": on_payload["pokemon"]["opponent_active"]["hp_percent"],
    }
    assert battle_state_context["self_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert battle_state_context["self_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert battle_state_context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert battle_state_context["opponent_active"]["status"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert battle_state_context["opponent_active"]["boosts"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert battle_state_context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert set(battle_state_context["field"]) == {"weather", "terrain", "screens", "hazards", "room"}
    assert all(value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD for value in battle_state_context["field"].values())
    assert battle_state_context["known_conditions"] == []

    assert '"turn_pipeline"' in on_prompt
    assert '"turn_order_context"' in on_prompt
    assert '"opponent_move_context"' in on_prompt
    assert '"battle_state_context"' in on_prompt
    assert "candidate events are not resolved outcomes" in on_prompt
    assert "limited planning/debug summary only, not full turn simulation" in on_prompt
    assert "limited planning context, not a resolved move order" in on_prompt
    assert "If opponent_move_context is present" in on_prompt
    assert "Candidate moves are not confirmed selected moves" in on_prompt
    assert "Do not infer hidden movesets" in on_prompt
    assert "If battle_state_context is present" in on_prompt
    assert "Unknown battle state fields must remain unknown" in on_prompt
    assert "Do not infer hidden items." in on_prompt
    assert "Do not infer EVs, IVs, or nature." in on_prompt
    assert "Do not infer boosts, status, weather, terrain, hazards, screens, or room unless explicitly provided." in on_prompt
    assert "Do not reverse-engineer hidden state from damage estimates or KO context." in on_prompt
    assert "not a resolved turn simulation" in on_prompt
    assert (
        "Do not claim post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, "
        "or full turn outcome"
    ) in on_prompt


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
        enable_battle_state_context=enabled,
    )

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    prompt_payload = _prompt_payload(prompt)
    assert "turn_pipeline" in prompt_payload
    assert "turn_order_context" in prompt_payload
    assert "opponent_move_context" not in prompt_payload
    assert "battle_state_context" in prompt_payload
    assert "If opponent_move_context is present" not in prompt
    assert "If battle_state_context is present" in prompt
