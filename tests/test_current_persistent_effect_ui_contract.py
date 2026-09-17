from PySide6.QtWidgets import QApplication

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
