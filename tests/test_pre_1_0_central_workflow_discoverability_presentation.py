from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QPushButton

import ui.main_window as main_window_module
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_battle_turn_status_is_persistent_and_presentation_only() -> None:
    _app()
    window = MainWindow()

    assert window.center_column.workflow_status_label.text() == "배틀: 비활성 · 턴: 미확인"
    assert window._active_session_id() is None
    assert window._current_trusted_turn_number is None

    window.center_column.set_battle_workflow_status(active=True, turn_number=99)
    assert window.center_column.workflow_status_label.text() == "배틀: 진행 중 · 턴: 99"
    assert window._active_session_id() is None
    assert window._current_trusted_turn_number is None

    window._refresh_battle_workflow_status()
    assert window.center_column.workflow_status_label.text() == "배틀: 비활성 · 턴: 미확인"
    window.close()


def test_central_shortcuts_reuse_existing_battle_and_turn_handlers(monkeypatch) -> None:
    _app()
    window = MainWindow()

    window.center_column.start_battle_button.click()
    assert window._active_session_id() is None
    assert window.center_column.workflow_status_label.text() == "배틀: 비활성 · 턴: 미확인"
    assert "select self and opponent" in window.statusBar().currentMessage()

    window.my_team_column.panels[0].pokemon_view = SimpleNamespace(en="pikachu")
    window.opponent_team_column.panels[0].pokemon_view = SimpleNamespace(en="eevee")
    window.center_column.start_battle_button.click()
    first_session = window._active_session_id()
    assert first_session == "ui-session-1"
    assert window.center_column.workflow_status_label.text() == "배틀: 진행 중 · 턴: 미확인"

    monkeypatch.setattr(main_window_module.QInputDialog, "getInt", lambda *args: (1, True))
    window.center_column.set_turn_button.click()
    assert window._current_trusted_turn_number == 1
    assert window.center_column.workflow_status_label.text() == "배틀: 진행 중 · 턴: 1"

    window.center_column.start_battle_button.click()
    assert window._active_session_id() == "ui-session-2"
    assert window._active_session_id() != first_session
    assert window._current_trusted_turn_number is None
    assert window.center_column.workflow_status_label.text() == "배틀: 진행 중 · 턴: 미확인"
    window.close()


def test_readiness_is_primary_korean_entry_and_strategy_remains_explicit() -> None:
    _app()
    panel = LLMAdvicePanel()
    readiness_routes: list[str] = []
    strategy_requests: list[bool] = []
    panel.readiness_input_requested.connect(readiness_routes.append)
    panel.deterministic_strategy_requested.connect(lambda: strategy_requests.append(True))

    assert panel.recommendation_section_label.text() == "추천 준비"
    assert panel.readiness_button.text() == "필요 정보 확인"
    assert panel.deterministic_strategy_button.text() == "전략 분석"
    assert panel.request_button.parentWidget() is panel.auxiliary_controls_widget
    assert panel.structured_request_button.parentWidget() is panel.auxiliary_controls_widget

    panel.set_recommendation_readiness({
        "status": "incomplete",
        "missing": [
            {"label": "Current HP needed", "action": "current_hp"},
            {"label": "Current ability unknown", "action": "current_ability"},
        ],
        "unsupported": [],
        "action": "current_hp",
    })
    assert "현재 HP" in panel.readiness_label.text()
    assert "현재 특성" in panel.readiness_label.text()
    assert panel.readiness_input_button.text() == "입력하기: 현재 HP"
    assert [button.text() for button in panel._readiness_extra_input_buttons] == ["입력하기: 현재 특성"]

    panel.readiness_input_button.click()
    panel._readiness_extra_input_buttons[0].click()
    assert readiness_routes == ["current_hp", "current_ability"]
    assert strategy_requests == []

    panel.deterministic_strategy_button.click()
    assert strategy_requests == [True]


def test_auxiliary_controls_are_grouped_by_user_semantics() -> None:
    _app()
    panel = LLMAdvicePanel()

    assert panel.current_state_section_label.text() == "현재 상태"
    assert panel.observed_section_label.text() == "관측 기록"
    assert panel.advanced_section_label.text() == "고급 / 특수"
    assert panel.llm_tools_section_label.text() == "LLM 도구"
    assert panel.reset_section_label.text() == "입력 표시 초기화"

    assert panel._current_state_buttons == [
        panel.current_hp_button,
        panel.current_condition_button,
        panel.current_ability_button,
        panel.current_type_button,
        panel.current_stat_stage_button,
        panel.current_field_state_button,
        panel.switch_permission_button,
    ]
    assert panel._observed_event_buttons == [
        panel.item_event_button,
        panel.current_observed_damage_button,
    ]
    assert panel.status_progression_button in panel._advanced_special_buttons
    assert panel.pending_status_action_result_button in panel._advanced_special_buttons
    assert panel.current_persistent_effect_button in panel._advanced_special_buttons
    assert panel.current_final_stat_button in panel._advanced_special_buttons
    assert panel.current_battle_format_button in panel._advanced_special_buttons
    assert panel.contact_status_result_button in panel._advanced_special_buttons
    assert panel.contact_reactive_damage_button in panel._advanced_special_buttons
    assert panel.battle_counter_button in panel._advanced_special_buttons

    assert panel.request_button in panel._llm_tool_buttons
    assert panel.structured_request_button in panel._llm_tool_buttons
    assert panel.field_profile_button in panel._llm_tool_buttons
    assert panel.turn_pipeline_checkbox.text() == "고급 LLM 컨텍스트 포함"

    assert panel.current_field_state_button.text() == "현재 전장 상태"
    assert panel.field_profile_button.text() == "추가 필드 프로필 (위험물/벽)"
    assert panel.current_field_state_button.text() != panel.field_profile_button.text()


def test_reset_controls_are_secondary_grouped_and_preserve_existing_signals() -> None:
    _app()
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.current_hp_session_reset_requested.connect(lambda: emitted.append("hp"))
    panel.current_condition_session_reset_requested.connect(lambda: emitted.append("condition"))

    assert panel.clear_current_hp_button in panel._reset_buttons
    assert panel.clear_current_conditions_button in panel._reset_buttons
    assert panel.clear_current_hp_button not in panel._current_state_buttons
    assert panel.clear_current_conditions_button not in panel._current_state_buttons
    assert panel.clear_current_hp_button.property("resetAction") is True
    assert panel.clear_current_hp_button.text() == "현재 HP 입력 표시 초기화"
    assert panel.clear_current_conditions_button.text() == "현재 상태이상 입력 표시 초기화"

    panel.clear_current_hp_button.click()
    panel.clear_current_conditions_button.click()
    assert emitted == ["hp", "condition"]
    assert all(isinstance(button, QPushButton) and button.minimumHeight() >= 32 for button in panel._reset_buttons)


def test_scroll_container_still_contains_every_grouped_auxiliary_action() -> None:
    app = _app()
    panel = LLMAdvicePanel()
    panel.resize(480, 700)
    panel.show()
    app.processEvents()

    expected = (
        panel._current_state_buttons
        + panel._observed_event_buttons
        + panel._advanced_special_buttons
        + panel._llm_tool_buttons
        + panel._reset_buttons
    )
    assert panel._auxiliary_input_buttons == expected
    assert all(button.parentWidget() is panel.auxiliary_controls_widget for button in expected)
    assert panel.auxiliary_scroll_area.verticalScrollBar().maximum() > 0
    panel.auxiliary_scroll_area.ensureWidgetVisible(panel.clear_battle_counter_button)
    app.processEvents()
    assert panel.auxiliary_scroll_area.verticalScrollBar().value() > 0
