from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_battle_state_context import build_current_ability_context_from_confirmations
from tests.test_advisor_payload_contract import _move, _panel, _window
from ui.main_window import MainWindow
from ui.widgets.current_ability_dialog import CurrentAbilityDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _ability(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "side": "self",
        "ability": "intimidate",
        "status": "user_confirmed",
        "source": "user_confirmed_current_ability",
        "confidence": "known",
    }
    candidate.update(overrides)
    return candidate


class _FakeAbilityDialog:
    def __init__(
        self,
        *,
        current_abilities: dict[str, dict[str, Any]],
        result: QDialog.DialogCode,
        ability: dict[str, Any] | None,
    ) -> None:
        self.current_abilities = deepcopy(current_abilities)
        self._result = result
        self.current_ability_confirmation = deepcopy(ability)

    def exec(self) -> QDialog.DialogCode:
        return self._result


def _window_with_panel() -> tuple[MainWindow, LLMAdvicePanel]:
    window = MainWindow.__new__(MainWindow)
    panel = LLMAdvicePanel()
    window._current_ability_confirmations = {}
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    return window, panel


def _payload_window() -> MainWindow:
    window = _window(
        _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")]),
        _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")]),
    )
    window._current_ability_confirmations = {}
    return window


def test_dialog_summary_and_apply_normalize_current_ability() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    dialog = CurrentAbilityDialog(
        current_abilities={"self": _ability(), "opponent": _ability(side="opponent", ability="unknown")}
    )

    assert "self: intimidate" in dialog.summary_label.text()
    assert "opponent: unknown" in dialog.summary_label.text()
    dialog.ability_combo.setEditText("Quark Drive")
    dialog._save_and_accept()

    assert dialog.current_ability_confirmation == _ability(ability="quark-drive")


def test_main_window_apply_replaces_side_and_keeps_other_side(monkeypatch: pytest.MonkeyPatch) -> None:
    window, panel = _window_with_panel()
    queued = [
        _FakeAbilityDialog(current_abilities={}, result=QDialog.DialogCode.Accepted, ability=_ability()),
        _FakeAbilityDialog(current_abilities={}, result=QDialog.DialogCode.Accepted, ability=_ability(ability="mold-breaker")),
        _FakeAbilityDialog(current_abilities={}, result=QDialog.DialogCode.Accepted, ability=_ability(side="opponent", ability="unknown")),
    ]
    monkeypatch.setattr(main_window_module, "CurrentAbilityDialog", lambda *, current_abilities, parent: queued.pop(0))

    window._open_current_ability_dialog()
    window._open_current_ability_dialog()
    window._open_current_ability_dialog()

    assert window._current_ability_confirmations == {
        "self": _ability(ability="mold-breaker"),
        "opponent": _ability(side="opponent", ability="unknown"),
    }
    assert panel.current_ability_button.text() == "Ability (2)"


def test_cancel_invalid_apply_and_clear_preserve_or_reset_state_without_advice_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = {"self": _ability()}
    window, panel = _window_with_panel()
    window._current_ability_confirmations = deepcopy(previous)
    queued = [
        _FakeAbilityDialog(current_abilities=previous, result=QDialog.DialogCode.Rejected, ability=_ability(ability="levitate")),
        _FakeAbilityDialog(current_abilities=previous, result=QDialog.DialogCode.Accepted, ability=_ability(ability="none")),
    ]
    monkeypatch.setattr(main_window_module, "CurrentAbilityDialog", lambda *, current_abilities, parent: queued.pop(0))
    advice_requests = 0

    def record_advice_request() -> None:
        nonlocal advice_requests
        advice_requests += 1

    panel.advice_requested.connect(record_advice_request)

    window._open_current_ability_dialog()
    window._open_current_ability_dialog()
    assert window._current_ability_confirmations == previous

    panel.current_ability_session_reset_requested.connect(window._clear_current_ability_confirmations)
    panel.clear_current_abilities_button.click()
    assert window._current_ability_confirmations == {}
    assert panel.current_ability_button.text() == "Ability"
    assert advice_requests == 0


def test_unknown_is_saved_but_none_and_candidate_lists_are_rejected() -> None:
    assert build_current_ability_context_from_confirmations([_ability(ability="unknown")]) == {
        "current_abilities": [_ability(ability="unknown")]
    }
    assert build_current_ability_context_from_confirmations([_ability(ability="none")]) is None
    assert build_current_ability_context_from_confirmations([_ability(ability="levitate / heatproof")]) is None


def test_limited_context_gate_controls_battle_input_without_resetting_session_state() -> None:
    window = _payload_window()
    abilities = {"self": _ability(), "opponent": _ability(side="opponent", ability="unknown")}
    window._current_ability_confirmations = deepcopy(abilities)

    off_input = window._build_llm_battle_input(include_current_ability_confirmations=False)
    on_input = window._build_llm_battle_input(include_current_ability_confirmations=True)

    assert window._current_ability_confirmations == abilities
    assert "current_ability_confirmations" not in off_input
    assert on_input["current_ability_confirmations"] == [abilities["self"], abilities["opponent"]]
