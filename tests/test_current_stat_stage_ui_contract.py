from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from ui.main_window import MainWindow
from ui.widgets.current_stat_stage_dialog import CurrentStatStageDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _stage(side: str = "self", stat: str = "attack", stage: int = -1) -> dict[str, object]:
    return {"side": side, "stat": stat, "stage": stage, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}


class _FakeDialog:
    def __init__(self, stage: dict[str, object] | None, accepted: bool = True, **_: object) -> None:
        self.current_stat_stage_confirmation = stage
        self._accepted = accepted
    def exec(self) -> QDialog.DialogCode:
        return QDialog.DialogCode.Accepted if self._accepted else QDialog.DialogCode.Rejected


def _window() -> tuple[MainWindow, LLMAdvicePanel]:
    window = MainWindow.__new__(MainWindow)
    panel = LLMAdvicePanel()
    window.center_column = SimpleNamespace(llm_advice_panel=panel)
    window._current_stat_stage_confirmations = {}
    return window, panel


def test_dialog_apply_and_readback() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentStatStageDialog(current_stages={("self", "attack"): _stage()})
    assert "self attack: -1" in dialog.summary_label.text()
    dialog.stage_spin.setValue(2)
    dialog._save_and_accept()
    assert dialog.current_stat_stage_confirmation == {**_stage(stage=2), "confidence": "known"}


def test_session_replaces_side_stat_keeps_others_cancel_and_clear(monkeypatch) -> None:
    window, panel = _window()
    queue = [_FakeDialog(_stage()), _FakeDialog(_stage(stage=2)), _FakeDialog(_stage("opponent", "speed", 2)), _FakeDialog(_stage("self", "speed", 1), accepted=False)]
    monkeypatch.setattr(main_window_module, "CurrentStatStageDialog", lambda **kwargs: queue.pop(0))
    window._open_current_stat_stage_dialog(); window._open_current_stat_stage_dialog(); window._open_current_stat_stage_dialog(); window._open_current_stat_stage_dialog()
    assert window._current_stat_stage_confirmations == {("self", "attack"): {**_stage(stage=2), "confidence": "known"}, ("opponent", "speed"): {**_stage("opponent", "speed", 2), "confidence": "known"}}
    assert panel.current_stat_stage_button.text() == "Stat stages (2)"
    window._clear_current_stat_stage_confirmations()
    assert window._current_stat_stage_confirmations == {}
    assert panel.current_stat_stage_button.text() == "Stat stages"
