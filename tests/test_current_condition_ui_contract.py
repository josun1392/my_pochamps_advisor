from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QDialog

import llm.advisor_client as advisor_client
import ui.main_window as main_window_module
from llm.advisor_battle_state_context import build_current_condition_context_from_confirmations
from tests.test_advisor_payload_contract import _move, _panel, _window
from ui.main_window import MainWindow
from ui.widgets.current_condition_dialog import CurrentConditionDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _condition(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "side": "self",
        "condition_type": "burn",
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
        "confidence": "known",
    }
    candidate.update(overrides)
    return candidate


class _FakeConditionDialog:
    def __init__(
        self,
        *,
        current_conditions: dict[str, dict[str, Any]],
        result: QDialog.DialogCode,
        condition: dict[str, Any] | None,
    ) -> None:
        self.current_conditions = deepcopy(current_conditions)
        self._result = result
        self.current_condition_confirmation = deepcopy(condition)

    def exec(self) -> QDialog.DialogCode:
        return self._result


def _window_with_panel() -> tuple[MainWindow, LLMAdvicePanel]:
    window = MainWindow.__new__(MainWindow)
    panel = LLMAdvicePanel()
    window._current_condition_confirmations = {}
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    return window, panel


def _payload_window() -> MainWindow:
    window = _window(
        _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")]),
        _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")]),
    )
    window._current_condition_confirmations = {}
    return window


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def test_dialog_shows_summary_and_applies_user_confirmed_current_condition() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = CurrentConditionDialog(current_conditions={"self": _condition(), "opponent": _condition(side="opponent", condition_type="unknown")})

    assert "self: burn" in dialog.summary_label.text()
    assert "opponent: unknown" in dialog.summary_label.text()
    dialog._save_and_accept()

    assert dialog.current_condition_confirmation == _condition()


def test_main_window_apply_replaces_same_side_and_keeps_other_side(monkeypatch: pytest.MonkeyPatch) -> None:
    window, panel = _window_with_panel()
    queued = [
        _FakeConditionDialog(current_conditions={}, result=QDialog.DialogCode.Accepted, condition=_condition()),
        _FakeConditionDialog(current_conditions={}, result=QDialog.DialogCode.Accepted, condition=_condition(condition_type="sleep")),
        _FakeConditionDialog(current_conditions={}, result=QDialog.DialogCode.Accepted, condition=_condition(side="opponent", condition_type="freeze")),
    ]
    monkeypatch.setattr(main_window_module, "CurrentConditionDialog", lambda *, current_conditions, parent: queued.pop(0))

    window._open_current_condition_dialog()
    window._open_current_condition_dialog()
    window._open_current_condition_dialog()

    assert window._current_condition_confirmations == {
        "self": _condition(condition_type="sleep"),
        "opponent": _condition(side="opponent", condition_type="freeze"),
    }
    assert panel.current_condition_button.text() == "Condition (2)"


def test_cancel_and_invalid_apply_preserve_existing_current_condition_state(monkeypatch: pytest.MonkeyPatch) -> None:
    previous = {"self": _condition()}
    window, _ = _window_with_panel()
    window._current_condition_confirmations = deepcopy(previous)
    queued = [
        _FakeConditionDialog(current_conditions=previous, result=QDialog.DialogCode.Rejected, condition=_condition(condition_type="sleep")),
        _FakeConditionDialog(current_conditions=previous, result=QDialog.DialogCode.Accepted, condition=_condition(exact_status_damage=1)),
    ]
    monkeypatch.setattr(main_window_module, "CurrentConditionDialog", lambda *, current_conditions, parent: queued.pop(0))

    window._open_current_condition_dialog()
    window._open_current_condition_dialog()

    assert window._current_condition_confirmations == previous


def test_none_and_unknown_remain_distinct_current_condition_values() -> None:
    none_context = build_current_condition_context_from_confirmations([_condition(condition_type="none")])
    unknown_context = build_current_condition_context_from_confirmations([_condition(condition_type="unknown")])

    assert none_context == {"current_conditions": [_condition(condition_type="none")]}
    assert unknown_context == {"current_conditions": [_condition(condition_type="unknown")]}
    assert none_context != unknown_context


def test_limited_context_gate_controls_battle_input_and_prompt_but_not_session_state() -> None:
    window = _payload_window()
    conditions = {
        "self": _condition(condition_type="burn"),
        "opponent": _condition(side="opponent", condition_type="unknown"),
    }
    window._current_condition_confirmations = deepcopy(conditions)

    off_input = window._build_llm_battle_input(include_current_condition_confirmations=False)
    on_input = window._build_llm_battle_input(include_current_condition_confirmations=True)
    off_prompt = advisor_client._build_ui_selected_prompt(off_input, enable_battle_state_context=False)
    on_prompt = advisor_client._build_ui_selected_prompt(on_input, enable_battle_state_context=True)

    assert window._current_condition_confirmations == conditions
    assert "current_condition_confirmations" not in off_input
    assert on_input["current_condition_confirmations"] == [conditions["self"], conditions["opponent"]]
    assert "current_condition_confirmations" not in _prompt_payload(off_prompt)
    assert "current_condition_confirmations" not in _prompt_payload(on_prompt)
    assert _prompt_payload(on_prompt)["condition_context"] == {
        "current_conditions": [conditions["self"], conditions["opponent"]]
    }
    assert "If condition_context is present" in on_prompt


def test_clear_action_resets_state_count_and_payload_candidate_without_advice_request() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window, panel = _window_with_panel()
    window._current_condition_confirmations = {"self": _condition()}
    panel.current_condition_session_reset_requested.connect(window._clear_current_condition_confirmations)
    window._update_current_condition_summary()
    advice_requests = 0

    def record_advice_request() -> None:
        nonlocal advice_requests
        advice_requests += 1

    panel.advice_requested.connect(record_advice_request)
    panel.clear_current_conditions_button.click()

    assert window._current_condition_confirmations == {}
    assert panel.current_condition_button.text() == "Condition"
    assert build_current_condition_context_from_confirmations([]) is None
    assert advice_requests == 0


def test_invalid_and_future_condition_candidates_are_omitted_from_payload_candidate() -> None:
    context = build_current_condition_context_from_confirmations(
        [
            _condition(),
            _condition(side="opponent", source="battle_log"),
            _condition(side="opponent", rng_roll=1),
        ]
    )

    assert context == {"current_conditions": [_condition()]}
    assert build_current_condition_context_from_confirmations([_condition(source="parser")]) is None
