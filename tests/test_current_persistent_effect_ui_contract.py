from PySide6.QtWidgets import QApplication

from ui.widgets.current_persistent_effect_dialog import CurrentPersistentEffectDialog


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
