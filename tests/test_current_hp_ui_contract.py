from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.widgets.current_hp_dialog import CurrentHPDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_current_hp_dialog_records_exact_snapshot_without_provider() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentHPDialog(current_hp={}); dialog.confirm_self.setChecked(True); dialog.current_spin.setValue(240); dialog.maximum_spin.setValue(300); dialog._save()
    assert dialog.current_hp_confirmation == {"side": "self", "current_hp": 240, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"}


def test_current_hp_panel_count_does_not_emit_advice_request() -> None:
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel(); emitted = []; panel.advice_requested.connect(lambda: emitted.append(True)); panel.set_current_hp_count(2)
    assert panel.current_hp_button.text() == "Current HP (2)" and emitted == []


def test_current_hp_dialog_can_confirm_both_active_sides_without_combining_records() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentHPDialog(current_hp={})
    dialog.confirm_self.setChecked(True); dialog.self_current_spin.setValue(240); dialog.self_maximum_spin.setValue(300)
    dialog.confirm_opponent.setChecked(True); dialog.opponent_current_spin.setValue(80); dialog.opponent_maximum_spin.setValue(100)
    dialog._save()
    assert dialog.current_hp_confirmations == [
        {"side": "self", "current_hp": 240, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
        {"side": "opponent", "current_hp": 80, "maximum_hp": 100, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"},
    ]


def test_current_hp_dialog_leaves_unticked_opponent_unknown_and_unwritten() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentHPDialog(current_hp={})
    dialog.confirm_self.setChecked(True); dialog.self_current_spin.setValue(50); dialog.self_maximum_spin.setValue(100)
    dialog.confirm_opponent.setChecked(False); dialog.opponent_current_spin.setValue(1); dialog.opponent_maximum_spin.setValue(1)
    dialog._save()
    assert [entry["side"] for entry in dialog.current_hp_confirmations] == ["self"]
