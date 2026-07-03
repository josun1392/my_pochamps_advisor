from __future__ import annotations

import json
from copy import deepcopy

import pytest
from PySide6.QtWidgets import QApplication

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
from tests.test_advisor_payload_contract import (
    _move,
    _opponent_move_ui_advice_flow_payload,
    _panel,
    _turn_pipeline_advice_flow_payload,
    _window,
)
from ui.widgets.llm_advice_panel import LLMAdvicePanel, TURN_PIPELINE_HELP_TEXT, TURN_PIPELINE_STATUS_TEXT


def _prompt_payload(prompt: str) -> dict:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _user_confirmed_item_profile(item_id: str) -> dict:
    return {"status": "user_confirmed", "source": "user_input", "item_id": item_id}


def _user_confirmed_field_profile(value: object) -> dict:
    return {"status": "user_confirmed", "source": "user_input", "value": value}


def _with_item_profiles(payload: dict, *, my_active: dict | None, opponent_active: dict | None) -> dict:
    payload = deepcopy(payload)
    payload["item_profiles"] = {
        "my_active": my_active,
        "opponent_active": opponent_active,
    }
    return payload


def _with_field_profiles(payload: dict, field_profiles: dict) -> dict:
    payload = deepcopy(payload)
    payload["field_profiles"] = field_profiles
    return payload


def _user_confirmed_item_ui_smoke_payload(
    *,
    my_active_item_profile: dict | None,
    opponent_active_item_profile: dict | None,
) -> dict:
    payload = _with_item_profiles(
        _opponent_move_ui_advice_flow_payload(),
        my_active=my_active_item_profile,
        opponent_active=opponent_active_item_profile,
    )
    payload["pokemon"]["my_active"]["name_en"] = "Garchomp"
    payload["pokemon"]["my_active"]["hp_percent"] = 100
    payload["pokemon"]["opponent_active"]["name_en"] = "Charizard"
    payload["pokemon"]["opponent_active"]["hp_percent"] = 87
    return payload


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
        "사용자 확인 아이템",
        "사용자 확인 필드 상태",
        "날씨/필드/룸/벽/설치물",
        "현재 컨텍스트",
        "확정 결과가 아니",
        "실제 선택 기술",
        "숨겨진 아이템/상태/랭크/필드",
        "턴 수",
        "만료",
        "턴 후 결과",
        "정확한 데미지",
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
        "상대 숨겨진 아이템",
        "추정 아이템",
        "추천 아이템",
        "자동 판별 아이템",
        "데미지 기반 아이템 추정",
        "확정 선후공",
        "확정 전투 결과",
        "확정 턴 결과입니다",
        "숨겨진 아이템일 가능성",
        "아이템 발동 확정",
        "상태이상을 추론",
        "랭크 변화를 추론",
        "필드 상태를 추론",
        "필드 상태로 데미지를 정확히 계산",
        "날씨/필드 턴 수를 확정",
        "다음 턴 결과를 확정",
        "벽/설치물 만료를 계산",
        "전체 턴 결과를 시뮬레이션",
        "필드 상태가 데미지를 확정",
        "필드 상태가 턴 수를 확정",
        "필드 상태가 만료를 확정",
        "턴 후 HP 확정",
        "아이템 소모 확정",
        "RNG 결과 확정",
        "RNG 확정",
        "스피드 타이 결과 확정",
        "speed tie 확정",
        "Quick Claw 발동 확정",
        "전체 턴 결과 확정",
        "full outcome 확정",
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


def test_limited_context_checkbox_item_profiles_are_mapped_only_when_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    payload = _with_item_profiles(
        _opponent_move_ui_advice_flow_payload(),
        my_active=_user_confirmed_item_profile("leftovers"),
        opponent_active=_user_confirmed_item_profile("choice-scarf"),
    )
    captured_prompts: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v11-9-items"
        captured_prompts.append(prompt)
        return (
            "Known user-confirmed items are limited context only; no item consumption or resolved outcome is inferred.",
            {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0},
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    def run_from_panel() -> None:
        enabled = panel.turn_pipeline_enabled()
        advisor_client.run_ui_selected_advice(
            payload,
            model="offline-v11-9-items",
            enable_turn_pipeline=enabled,
            enable_turn_order_context=enabled,
            enable_opponent_move_context=enabled,
            enable_battle_state_context=enabled,
        )

    run_from_panel()
    panel.turn_pipeline_checkbox.setChecked(True)
    run_from_panel()

    assert len(captured_prompts) == 2
    off_prompt, on_prompt = captured_prompts
    off_payload = _prompt_payload(off_prompt)
    on_payload = _prompt_payload(on_prompt)

    assert "battle_state_context" not in off_payload
    assert '"battle_state_context"' not in off_prompt
    assert "If battle_state_context is present" not in off_prompt

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
    assert battle_state_context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert battle_state_context["opponent_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "choice-scarf",
    }
    assert '"value": "leftovers"' in on_prompt
    assert '"value": "choice-scarf"' in on_prompt
    assert "If battle_state_context is present" in on_prompt
    assert "Do not claim post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation" in on_prompt

    for forbidden_field in (
        "item_consumed",
        "item_consumption",
        "post_turn_hp",
        "rng_resolved",
        "speed_tie_resolved",
        "quick_claw_activated",
        "full_turn_result",
        "resolved_outcome",
    ):
        assert forbidden_field not in battle_state_context
        assert forbidden_field not in battle_state_context["self_active"]
        assert forbidden_field not in battle_state_context["opponent_active"]


def test_limited_context_checkbox_field_profiles_are_mapped_only_when_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    payload = _with_field_profiles(
        _with_item_profiles(
            _opponent_move_ui_advice_flow_payload(),
            my_active=_user_confirmed_item_profile("leftovers"),
            opponent_active=_user_confirmed_item_profile("choice-scarf"),
        ),
        {
            "weather": _user_confirmed_field_profile("rain"),
            "terrain": _user_confirmed_field_profile("electric_terrain"),
            "room": _user_confirmed_field_profile("trick_room"),
            "screens": _user_confirmed_field_profile({"self": ["reflect"], "opponent": ["light_screen"]}),
            "hazards": _user_confirmed_field_profile({"self": [], "opponent": ["stealth_rock"]}),
        },
    )
    captured_prompts: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v12-12-fields"
        captured_prompts.append(prompt)
        return (
            "Known field entries are current context only; duration, expiration, post-turn state, "
            "damage precision, and full outcomes remain unresolved.",
            {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0},
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"mocked": True})

    def run_from_panel() -> None:
        enabled = panel.turn_pipeline_enabled()
        advisor_client.run_ui_selected_advice(
            payload,
            model="offline-v12-12-fields",
            enable_turn_pipeline=enabled,
            enable_turn_order_context=enabled,
            enable_opponent_move_context=enabled,
            enable_battle_state_context=enabled,
        )

    run_from_panel()
    panel.turn_pipeline_checkbox.setChecked(True)
    run_from_panel()

    assert len(captured_prompts) == 2
    off_prompt, on_prompt = captured_prompts
    off_payload = _prompt_payload(off_prompt)
    on_payload = _prompt_payload(on_prompt)

    assert "battle_state_context" not in off_payload
    assert "field_profiles" not in off_payload
    assert '"field_profiles"' not in off_prompt
    assert '"battle_state_context"' not in off_prompt

    assert "field_profiles" not in on_payload
    assert on_payload["turn_pipeline"]["simulated"] == "limited"
    assert on_payload["turn_order_context"]["kind"] == "deterministic_turn_order_context"
    assert on_payload["opponent_move_context"]["kind"] == "opponent_move_context"
    assert on_payload["battle_state_context"]["kind"] == "battle_state_context"
    battle_state_context = on_payload["battle_state_context"]
    assert battle_state_context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert battle_state_context["opponent_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "choice-scarf",
    }
    assert battle_state_context["field"]["weather"] == {"known": True, "source": "user_confirmed", "value": "rain"}
    assert battle_state_context["field"]["terrain"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "electric_terrain",
    }
    assert battle_state_context["field"]["room"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "trick_room",
    }
    assert battle_state_context["field"]["screens"] == {
        "known": True,
        "source": "user_confirmed",
        "value": {"self": ["reflect"], "opponent": ["light_screen"]},
    }
    assert battle_state_context["field"]["hazards"] == {
        "known": True,
        "source": "user_confirmed",
        "value": {"self": [], "opponent": ["stealth_rock"]},
    }
    assert "If battle_state_context is present" in on_prompt

    for forbidden_field in (
        "duration",
        "expiration",
        "post_turn",
        "damage_precision",
        "resolved_outcome",
        "full_turn_result",
    ):
        assert forbidden_field not in battle_state_context
        assert forbidden_field not in battle_state_context["field"]


def test_field_state_ui_end_to_end_offline_smoke_from_saved_dialog_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        item_profile=_user_confirmed_item_profile("leftovers"),
    )
    opponent_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        item_profile=_user_confirmed_item_profile("choice-scarf"),
    )
    opponent_panel.current_hp_percent = 87
    window = _window(my_panel, opponent_panel)
    window._field_profiles = {
        "weather": _user_confirmed_field_profile("rain"),
        "terrain": _user_confirmed_field_profile("electric_terrain"),
        "room": _user_confirmed_field_profile("trick_room"),
        "screens": _user_confirmed_field_profile({"self": ["reflect"], "opponent": ["light_screen"]}),
        "hazards": _user_confirmed_field_profile({"self": [], "opponent": ["stealth_rock"]}),
    }
    battle_input = window._build_llm_battle_input()
    captured_prompts: list[str] = []
    logged_usages: list[dict[str, int]] = []
    mocked_responses: list[str] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v12-18-field-ui"
        captured_prompts.append(prompt)
        response = (
            "Known field entries are user-confirmed current context only. They do not resolve duration, "
            "expiration, post-turn state, exact damage, or the full turn outcome."
        )
        mocked_responses.append(response)
        return response, {"input_tokens": 70 + len(captured_prompts), "output_tokens": 12, "cached_tokens": 0}

    def fake_log_advisor_call(*, model: str, usage: dict[str, int], game_id: str) -> dict[str, object]:
        assert model == "offline-v12-18-field-ui"
        assert game_id == "ui_selected_pokemon_v0_6"
        logged_usages.append(usage)
        return {"mocked": True, "call_index": len(logged_usages)}

    def run_from_panel() -> tuple[str, dict[str, int], dict[str, object]]:
        enabled = panel.turn_pipeline_enabled()
        return advisor_client.run_ui_selected_advice(
            battle_input,
            model="offline-v12-18-field-ui",
            enable_turn_pipeline=enabled,
            enable_turn_order_context=enabled,
            enable_opponent_move_context=enabled,
            enable_battle_state_context=enabled,
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", fake_log_advisor_call)

    assert panel.turn_pipeline_checkbox.isChecked() is False
    off_response, off_usage, off_summary = run_from_panel()

    panel.turn_pipeline_checkbox.setChecked(True)
    on_response, on_usage, on_summary = run_from_panel()

    assert len(captured_prompts) == 2
    assert len(logged_usages) == 2
    assert off_response == mocked_responses[0]
    assert on_response == mocked_responses[1]
    assert off_usage == {"input_tokens": 71, "output_tokens": 12, "cached_tokens": 0}
    assert on_usage == {"input_tokens": 72, "output_tokens": 12, "cached_tokens": 0}
    assert off_summary == {"mocked": True, "call_index": 1}
    assert on_summary == {"mocked": True, "call_index": 2}

    off_prompt, on_prompt = captured_prompts
    off_payload = _prompt_payload(off_prompt)
    on_payload = _prompt_payload(on_prompt)

    assert "battle_state_context" not in off_payload
    assert "field_profiles" not in off_payload
    assert '"field_profiles"' not in off_prompt
    assert '"battle_state_context"' not in off_prompt
    for serialized_field_value in (
        '"value": "rain"',
        '"value": "electric_terrain"',
        '"value": "trick_room"',
        '"reflect"',
        '"light_screen"',
        '"stealth_rock"',
    ):
        assert serialized_field_value not in off_prompt

    assert "field_profiles" not in on_payload
    assert on_payload["turn_pipeline"]["simulated"] == "limited"
    assert on_payload["turn_order_context"]["kind"] == "deterministic_turn_order_context"
    assert on_payload["opponent_move_context"]["kind"] == "opponent_move_context"
    assert on_payload["battle_state_context"]["kind"] == "battle_state_context"
    battle_state_context = on_payload["battle_state_context"]
    assert battle_state_context["self_active"]["species"] == {"source": "visible_ui", "name": "garchomp"}
    assert battle_state_context["self_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 100}
    assert battle_state_context["opponent_active"]["species"] == {"source": "visible_ui", "name": "charizard"}
    assert battle_state_context["opponent_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 87}
    assert battle_state_context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert battle_state_context["opponent_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "choice-scarf",
    }
    assert battle_state_context["field"]["weather"] == {"known": True, "source": "user_confirmed", "value": "rain"}
    assert battle_state_context["field"]["terrain"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "electric_terrain",
    }
    assert battle_state_context["field"]["room"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "trick_room",
    }
    assert battle_state_context["field"]["screens"] == {
        "known": True,
        "source": "user_confirmed",
        "value": {"self": ["reflect"], "opponent": ["light_screen"]},
    }
    assert battle_state_context["field"]["hazards"] == {
        "known": True,
        "source": "user_confirmed",
        "value": {"self": [], "opponent": ["stealth_rock"]},
    }
    for serialized_field_value in (
        '"value": "rain"',
        '"value": "electric_terrain"',
        '"value": "trick_room"',
        '"reflect"',
        '"light_screen"',
        '"stealth_rock"',
    ):
        assert serialized_field_value in on_prompt
    assert "If battle_state_context is present" in on_prompt
    assert "Do not claim post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation" in on_prompt

    for response in (off_response, on_response):
        response_lower = response.lower()
        for unsafe_phrase in (
            "rain will last",
            "terrain expires this turn",
            "reflect definitely remains after the turn",
            "stealth rock damage is precisely calculated here",
            "damage is guaranteed",
            "full turn outcome is resolved",
            "field was inferred from damage",
            "hidden field exists",
        ):
            assert unsafe_phrase not in response_lower
    for forbidden_field in (
        "duration_turns",
        "expiration",
        "post_turn",
        "damage_precision",
        "resolved_outcome",
        "full_turn_result",
    ):
        assert forbidden_field not in battle_state_context
        assert forbidden_field not in battle_state_context["field"]


@pytest.mark.parametrize(
    ("field_profiles", "expected_weather"),
    [
        ({}, BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        ({"weather": _user_confirmed_field_profile("unknown")}, BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        (
            {"weather": _user_confirmed_field_profile("none")},
            {"known": True, "source": "user_confirmed", "value": "none"},
        ),
        (
            {"weather": {"status": "user_confirmed", "source": "context_derived", "value": "rain"}},
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
        ),
        (
            {"weather": {"status": "user_confirmed", "source": "calculated_from_visible", "value": "rain"}},
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
        ),
        (
            {"weather": {"status": "user_confirmed", "source": "user_input"}},
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
        ),
    ],
)
def test_limited_context_checkbox_on_field_profile_metadata_matrix(
    field_profiles: dict,
    expected_weather: dict,
) -> None:
    payload = _with_field_profiles(_opponent_move_ui_advice_flow_payload(), field_profiles)

    prompt = advisor_client._build_ui_selected_prompt(
        payload,
        enable_turn_pipeline=True,
        enable_turn_order_context=True,
        enable_opponent_move_context=True,
        enable_battle_state_context=True,
    )
    prompt_payload = _prompt_payload(prompt)
    battle_state_context = prompt_payload["battle_state_context"]

    assert "field_profiles" not in prompt_payload
    assert battle_state_context["field"]["weather"] == expected_weather
    for key in ("terrain", "screens", "hazards", "room"):
        assert battle_state_context["field"][key] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert "If battle_state_context is present" in prompt


def test_user_confirmed_item_ui_offline_smoke_covers_checkbox_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    valid_payload = _user_confirmed_item_ui_smoke_payload(
        my_active_item_profile=_user_confirmed_item_profile("leftovers"),
        opponent_active_item_profile=_user_confirmed_item_profile("choice-scarf"),
    )
    malformed_or_forbidden_payload = _user_confirmed_item_ui_smoke_payload(
        my_active_item_profile={"status": "user_confirmed", "source": "user_input"},
        opponent_active_item_profile={
            "status": "user_confirmed",
            "source": "context_derived",
            "item_id": "choice-scarf",
        },
    )
    captured_prompts: list[str] = []
    logged_usages: list[dict[str, int]] = []

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        assert model == "offline-v11-11-items"
        captured_prompts.append(prompt)
        response = (
            "User-confirmed items are known context, but they do not by themselves resolve activation, "
            "consumption, post-turn HP, RNG, speed ties, Quick Claw activation, selected opponent moves, "
            "or the complete resolved result."
        )
        return response, {"input_tokens": 50 + len(captured_prompts), "output_tokens": 11, "cached_tokens": 0}

    def fake_log_advisor_call(*, model: str, usage: dict[str, int], game_id: str) -> dict[str, object]:
        assert model == "offline-v11-11-items"
        assert game_id == "ui_selected_pokemon_v0_6"
        logged_usages.append(usage)
        return {"mocked": True, "call_index": len(logged_usages)}

    def run_from_panel(payload: dict) -> tuple[str, dict[str, int], dict[str, object]]:
        enabled = panel.turn_pipeline_enabled()
        return advisor_client.run_ui_selected_advice(
            payload,
            model="offline-v11-11-items",
            enable_turn_pipeline=enabled,
            enable_turn_order_context=enabled,
            enable_opponent_move_context=enabled,
            enable_battle_state_context=enabled,
        )

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", fake_log_advisor_call)

    panel.turn_pipeline_checkbox.setChecked(True)
    panel.turn_pipeline_checkbox.setChecked(False)
    assert captured_prompts == []
    assert logged_usages == []

    off_response, off_usage, off_summary = run_from_panel(valid_payload)

    panel.turn_pipeline_checkbox.setChecked(True)
    on_response, on_usage, on_summary = run_from_panel(valid_payload)
    forbidden_response, forbidden_usage, forbidden_summary = run_from_panel(malformed_or_forbidden_payload)

    assert len(captured_prompts) == 3
    assert len(logged_usages) == 3
    assert off_usage == {"input_tokens": 51, "output_tokens": 11, "cached_tokens": 0}
    assert on_usage == {"input_tokens": 52, "output_tokens": 11, "cached_tokens": 0}
    assert forbidden_usage == {"input_tokens": 53, "output_tokens": 11, "cached_tokens": 0}
    assert off_summary == {"mocked": True, "call_index": 1}
    assert on_summary == {"mocked": True, "call_index": 2}
    assert forbidden_summary == {"mocked": True, "call_index": 3}

    for response in (off_response, on_response, forbidden_response):
        response_lower = response.lower()
        for forbidden_phrase in (
            "item activates",
            "item is consumed",
            "post-turn hp will be",
            "rng resolved",
            "speed tie resolved",
            "quick claw activates",
            "full turn outcome",
            "opponent selected move certainty",
            "hidden item inference",
        ):
            assert forbidden_phrase not in response_lower

    off_prompt, on_prompt, forbidden_prompt = captured_prompts
    off_payload = _prompt_payload(off_prompt)
    on_payload = _prompt_payload(on_prompt)
    forbidden_payload = _prompt_payload(forbidden_prompt)

    assert "battle_state_context" not in off_payload
    assert '"battle_state_context"' not in off_prompt
    assert "If battle_state_context is present" not in off_prompt
    assert '"value": "leftovers"' not in off_prompt
    assert '"value": "choice-scarf"' not in off_prompt

    assert on_payload["turn_pipeline"]["simulated"] == "limited"
    assert on_payload["turn_order_context"]["kind"] == "deterministic_turn_order_context"
    assert on_payload["opponent_move_context"]["kind"] == "opponent_move_context"
    assert on_payload["battle_state_context"]["kind"] == "battle_state_context"
    on_context = on_payload["battle_state_context"]
    assert on_context["self_active"]["species"] == {"source": "visible_ui", "name": "Garchomp"}
    assert on_context["self_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 100}
    assert on_context["opponent_active"]["species"] == {"source": "visible_ui", "name": "Charizard"}
    assert on_context["opponent_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 87}
    assert on_context["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert on_context["opponent_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "choice-scarf",
    }
    assert all(value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD for value in on_context["field"].values())
    assert on_context["known_conditions"] == []
    assert '"value": "leftovers"' in on_prompt
    assert '"value": "choice-scarf"' in on_prompt
    assert "If battle_state_context is present" in on_prompt
    assert "Do not claim post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation" in on_prompt

    forbidden_context = forbidden_payload["battle_state_context"]
    assert forbidden_context["self_active"]["species"] == {"source": "visible_ui", "name": "Garchomp"}
    assert forbidden_context["self_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 100}
    assert forbidden_context["opponent_active"]["species"] == {"source": "visible_ui", "name": "Charizard"}
    assert forbidden_context["opponent_active"]["current_hp_percent"] == {"source": "visible_ui", "value": 87}
    assert forbidden_context["self_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert forbidden_context["opponent_active"]["item"] == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD
    assert '"value": "leftovers"' not in forbidden_prompt
    assert '"value": "choice-scarf"' not in forbidden_prompt

    for context in (on_context, forbidden_context):
        for forbidden_field in (
            "item_activated",
            "item_consumed",
            "item_consumption",
            "post_turn_hp",
            "rng_resolved",
            "speed_tie_resolved",
            "quick_claw_activated",
            "full_turn_result",
            "resolved_outcome",
        ):
            assert forbidden_field not in context
            assert forbidden_field not in context["self_active"]
            assert forbidden_field not in context["opponent_active"]


@pytest.mark.parametrize(
    ("item_profiles", "expected_self_item", "expected_opponent_item"),
    [
        (None, BATTLE_STATE_CONTEXT_UNKNOWN_FIELD, BATTLE_STATE_CONTEXT_UNKNOWN_FIELD),
        (
            {
                "my_active": {"status": "user_confirmed", "source": "user_input"},
                "opponent_active": {"status": "user_confirmed", "source": "user_input"},
            },
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
        ),
        (
            {
                "my_active": {"status": "unknown", "source": "user_input", "item_id": "leftovers"},
                "opponent_active": {"status": "none", "source": "user_input", "item_id": "choice-scarf"},
            },
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
        ),
        (
            {
                "my_active": {"status": "user_confirmed", "source": "visible_ui", "item_id": "leftovers"},
                "opponent_active": {
                    "status": "user_confirmed",
                    "source": "context_derived",
                    "item_id": "choice-scarf",
                },
            },
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
            BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
        ),
        (
            {
                "my_active": _user_confirmed_item_profile("leftovers"),
                "opponent_active": _user_confirmed_item_profile("choice-scarf"),
            },
            {"known": True, "source": "user_confirmed", "value": "leftovers"},
            {"known": True, "source": "user_confirmed", "value": "choice-scarf"},
        ),
    ],
)
def test_limited_context_checkbox_on_item_profile_metadata_matrix(
    item_profiles: dict | None,
    expected_self_item: dict,
    expected_opponent_item: dict,
) -> None:
    payload = deepcopy(_turn_pipeline_advice_flow_payload())
    if item_profiles is None:
        payload.pop("item_profiles", None)
    else:
        payload["item_profiles"] = item_profiles

    prompt = advisor_client._build_ui_selected_prompt(
        payload,
        enable_turn_pipeline=True,
        enable_turn_order_context=True,
        enable_opponent_move_context=True,
        enable_battle_state_context=True,
    )
    prompt_payload = _prompt_payload(prompt)
    battle_state_context = prompt_payload["battle_state_context"]

    assert battle_state_context["self_active"]["species"] == {
        "source": "visible_ui",
        "name": prompt_payload["pokemon"]["my_active"]["name_en"],
    }
    assert battle_state_context["opponent_active"]["current_hp_percent"] == {
        "source": "visible_ui",
        "value": prompt_payload["pokemon"]["opponent_active"]["hp_percent"],
    }
    assert battle_state_context["self_active"]["item"] == expected_self_item
    assert battle_state_context["opponent_active"]["item"] == expected_opponent_item
    assert all(value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD for value in battle_state_context["field"].values())
    assert battle_state_context["known_conditions"] == []
    assert "If battle_state_context is present" in prompt
