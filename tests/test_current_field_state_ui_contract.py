from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from ui.main_window import MainWindow
from ui.widgets.current_field_state_dialog import CurrentFieldStateDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _field(weather: str = "rain") -> dict[str, object]:
    return {"weather": weather, "terrain": "none", "global_effects": [], "side_effects": [{"side": "self", "effect": "reflect"}], "status": "user_confirmed", "source": "user_confirmed_current_field_state"}


class _FakeDialog:
    def __init__(self, snapshot: dict[str, object] | None, accepted: bool = True, **_: object) -> None:
        self.current_field_state_confirmation = snapshot
        self._accepted = accepted

    def exec(self) -> QDialog.DialogCode:
        return QDialog.DialogCode.Accepted if self._accepted else QDialog.DialogCode.Rejected


def _window() -> tuple[MainWindow, LLMAdvicePanel]:
    QApplication.instance() or QApplication([])
    window = MainWindow.__new__(MainWindow)
    panel = LLMAdvicePanel()
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    window._current_field_state_confirmation = None
    return window, panel


def test_field_dialog_apply_readback_and_snapshot_normalization() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentFieldStateDialog(current_field=_field())
    assert "Field snapshot saved" in dialog.summary_label.text()
    dialog.weather.setCurrentText("snow")
    dialog._save()
    assert dialog.current_field_state_confirmation is not None
    assert dialog.current_field_state_confirmation["weather"] == "snow"
    assert dialog.current_field_state_confirmation["confidence"] == "known"


def test_grounded_confirmation_is_explicit_and_unknown_by_default() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentFieldStateDialog(current_field=_field())
    assert dialog.grounded_context_confirmation is None
    dialog.self_grounded.setCurrentText("known_grounded")
    dialog.opponent_grounded.setCurrentText("known_ungrounded")
    dialog._save()
    assert dialog.grounded_context_confirmation == {
        "self": {"status": "known_grounded", "provenance": "user_confirmed_current"},
        "opponent": {"status": "known_ungrounded", "provenance": "user_confirmed_current"},
    }


def test_field_session_apply_cancel_clear_and_count(monkeypatch) -> None:
    window, panel = _window()
    dialogs = [_FakeDialog(_field()), _FakeDialog(_field("sun")), _FakeDialog(_field("snow"), accepted=False)]
    monkeypatch.setattr(main_window_module, "CurrentFieldStateDialog", lambda **kwargs: dialogs.pop(0))
    window._open_current_field_state_dialog(); window._open_current_field_state_dialog(); window._open_current_field_state_dialog()
    assert window._current_field_state_confirmation["weather"] == "sun"
    assert panel.current_field_state_button.text() == "Field state (3)"
    window._grounded_context_confirmation = {
        "self": {"status": "known_grounded", "provenance": "user_confirmed_current"},
        "opponent": {"status": "known_ungrounded", "provenance": "user_confirmed_current"},
    }
    window._clear_current_field_state_confirmation()
    assert window._current_field_state_confirmation is None
    assert window._grounded_context_confirmation == {
        "self": {"status": "unknown", "provenance": "unknown"},
        "opponent": {"status": "unknown", "provenance": "unknown"},
    }
    assert panel.current_field_state_button.text() == "Field state"
