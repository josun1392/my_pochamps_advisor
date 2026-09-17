from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class CurrentPersistentEffectDialog(QDialog):
    """Capture one explicit present-tense persistent-effect observation."""
    def __init__(self, *, current_effects: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent); self.setWindowTitle("Persistent Effects")
        self._current_effects = deepcopy(current_effects or {}); self._confirmation = None
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Current persistent effect"))
        self.summary_label = QLabel(self._summary()); self.summary_label.setWordWrap(True); layout.addWidget(self.summary_label)
        form = QFormLayout(); self.side_combo = self._combo((("self", "Self"), ("opponent", "Opponent")))
        self.family_combo = self._combo((("aqua_ring", "Aqua Ring"), ("ingrain", "Ingrain"), ("leech_seed", "Leech Seed")))
        self.state_combo = self._combo((("active", "Active"), ("inactive", "Inactive")))
        self.source_side_combo = self._combo((("opponent", "Opponent"), ("self", "Self")))
        self.source_slot_combo = self._combo(tuple((index, f"Slot {index}") for index in range(6)))
        self.family_combo.currentIndexChanged.connect(self._source_visibility); self.state_combo.currentIndexChanged.connect(self._source_visibility)
        form.addRow("Side", self.side_combo); form.addRow("Family", self.family_combo); form.addRow("Current state", self.state_combo); form.addRow("Leech Seed source side", self.source_side_combo); form.addRow("Leech Seed source slot", self.source_slot_combo); layout.addLayout(form)
        hint = QLabel("Records only an explicit current observation. Missing effects remain unknown."); hint.setWordWrap(True); layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self._source_visibility()

    @property
    def persistent_effect_confirmation(self): return deepcopy(self._confirmation)

    def _source_visibility(self):
        show = self.family_combo.currentData() == "leech_seed" and self.state_combo.currentData() == "active"
        self.source_side_combo.setVisible(show); self.source_slot_combo.setVisible(show)

    def _save(self):
        row = {"side": self.side_combo.currentData(), "family": self.family_combo.currentData(), "persistent_state": self.state_combo.currentData()}
        if row["family"] == "leech_seed" and row["persistent_state"] == "active": row.update(source_side=self.source_side_combo.currentData(), source_slot_index=self.source_slot_combo.currentData())
        self._confirmation = row; self.accept()

    def _summary(self):
        if not self._current_effects: return "No persistent-effect confirmations saved."
        lines = [f"{key}: {value.get('persistent_state', 'unknown')}" for key, value in sorted(self._current_effects.items()) if isinstance(value, dict)]
        return "\n".join(lines) if lines else "No persistent-effect confirmations saved."

    @staticmethod
    def _combo(options):
        combo = QComboBox()
        for value, label in options: combo.addItem(label, value)
        return combo
