from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication, QDialog

import ui.main_window as main_window_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from ui.main_window import MainWindow
from ui.widgets.current_persistent_effect_dialog import CurrentPersistentEffectDialog
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def test_dialog_captures_explicit_aqua_ring_and_never_offers_unknown():
    QApplication.instance() or QApplication([])
    dialog = CurrentPersistentEffectDialog()
    assert dialog.state_combo.findData("unknown") == -1
    dialog.family_combo.setCurrentIndex(dialog.family_combo.findData("aqua_ring")); dialog.state_combo.setCurrentIndex(dialog.state_combo.findData("active")); dialog._save()
    assert dialog.persistent_effect_confirmation == {"side": "self", "family": "aqua_ring", "persistent_state": "active"}


def test_leech_seed_active_includes_source_and_inactive_drops_it():
    QApplication.instance() or QApplication([])
    dialog = CurrentPersistentEffectDialog(); dialog.family_combo.setCurrentIndex(dialog.family_combo.findData("leech_seed")); dialog.state_combo.setCurrentIndex(dialog.state_combo.findData("active")); dialog._save()
    assert dialog.persistent_effect_confirmation["source_side"] == "opponent"
    dialog.state_combo.setCurrentIndex(dialog.state_combo.findData("inactive")); dialog._save()
    assert dialog.persistent_effect_confirmation == {"side": "self", "family": "leech_seed", "persistent_state": "inactive"}


def test_dialog_summary_is_identity_bound_presentation_only_and_panel_running_state_disables_button():
    QApplication.instance() or QApplication([])
    effects = {"self:1:raichu:aqua_ring": {"persistent_state": "active"}}
    dialog = CurrentPersistentEffectDialog(current_effects=effects)
    assert "self:1:raichu:aqua_ring: active" in dialog.summary_label.text()
    panel = LLMAdvicePanel(); panel.set_current_persistent_effect_count(1)
    assert panel.current_persistent_effect_button.text() == "Persistent Effects (1)"
    panel.set_running(True); assert not panel.current_persistent_effect_button.isEnabled()
    panel.set_running(False); assert panel.current_persistent_effect_button.isEnabled()


class _Dialog:
    def __init__(self, row, accepted=True): self.persistent_effect_confirmation = row; self.accepted = accepted
    def exec(self): return QDialog.DialogCode.Accepted if self.accepted else QDialog.DialogCode.Rejected


def _window():
    window = MainWindow.__new__(MainWindow); panel = LLMAdvicePanel(); state = create_unknown_bootstrap_battle_state("persistent-ui", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"): state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    window._observation_runtime_session_manager = BattleObservationRuntimeSessionManager.create("persistent-ui", state)["manager"]
    window._current_persistent_effect_confirmations = {}; window._current_trusted_turn_number = 1; window.center_column = SimpleNamespace(llm_advice_panel=panel)
    return window, panel


def test_mainwindow_resolved_admission_updates_count_cancel_and_rejection_preserve_it(monkeypatch: pytest.MonkeyPatch):
    window, panel = _window(); row = {"side": "self", "family": "aqua_ring", "persistent_state": "active"}
    monkeypatch.setattr(main_window_module, "CurrentPersistentEffectDialog", lambda **_: _Dialog(row))
    window._open_current_persistent_effect_dialog()
    assert len(window._current_persistent_effect_confirmations) == 1 and panel.current_persistent_effect_button.text() == "Persistent Effects (1)"
    before = dict(window._current_persistent_effect_confirmations)
    monkeypatch.setattr(main_window_module, "CurrentPersistentEffectDialog", lambda **_: _Dialog(row, accepted=False)); window._open_current_persistent_effect_dialog()
    assert window._current_persistent_effect_confirmations == before and panel.current_persistent_effect_button.text() == "Persistent Effects (1)"
    bad = {"side": "self", "family": "leech_seed", "persistent_state": "active", "source_side": "self", "source_slot_index": 0}
    monkeypatch.setattr(main_window_module, "CurrentPersistentEffectDialog", lambda **_: _Dialog(bad)); window._open_current_persistent_effect_dialog()
    assert window._current_persistent_effect_confirmations == before and panel.current_persistent_effect_button.text() == "Persistent Effects (1)"
