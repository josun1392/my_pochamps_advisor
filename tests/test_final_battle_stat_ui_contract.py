from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.widgets.current_final_stat_dialog import CurrentFinalStatDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_final_stat_dialog_records_max_hp_or_stage_unmodified_stat_without_provider() -> None:
    QApplication.instance() or QApplication([])
    dialog = CurrentFinalStatDialog(current_stats={})
    dialog.value_spin.setValue(301)
    dialog._save()
    assert dialog.current_final_stat_confirmation == {"side": "self", "stat": "hp", "value": 301, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def test_final_stat_panel_count_does_not_emit_advice_request() -> None:
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel(); emitted = []
    panel.advice_requested.connect(lambda: emitted.append(True))
    panel.set_current_final_stat_count(2)
    assert panel.current_final_stat_button.text() == "Final stats (2)"
    assert emitted == []
