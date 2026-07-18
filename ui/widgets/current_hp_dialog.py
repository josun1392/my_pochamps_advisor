from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_user_confirmed_current_hp


class CurrentHPDialog(QDialog):
    def __init__(self, *, current_hp: dict[str, dict[str, Any]] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current HP")
        self._current, self._result = deepcopy(current_hp or {}), None
        layout = QVBoxLayout(self); self.summary_label = QLabel(); layout.addWidget(self.summary_label)
        form = QFormLayout(); self.side_combo = QComboBox(); self.side_combo.addItem("Self", "self"); self.side_combo.addItem("Opponent", "opponent")
        self.current_spin, self.maximum_spin = QSpinBox(), QSpinBox()
        for spin in (self.current_spin, self.maximum_spin): spin.setRange(0, 9999)
        self.maximum_spin.setMinimum(1); self.side_combo.currentIndexChanged.connect(self._load)
        form.addRow("Side", self.side_combo); form.addRow("Current HP", self.current_spin); form.addRow("Maximum HP", self.maximum_spin); layout.addLayout(form)
        layout.addWidget(QLabel("Records exact user-confirmed current and maximum HP; visible percent is not converted."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons); self._refresh(); self._load()
    @property
    def current_hp_confirmation(self) -> dict[str, Any] | None: return deepcopy(self._result) if self._result else None
    def _refresh(self) -> None: self.summary_label.setText("\n".join(f"{side}: {entry['current_hp']}/{entry['maximum_hp']}" for side, entry in sorted(self._current.items())) or "No exact HP saved.")
    def _load(self) -> None:
        entry = self._current.get(self.side_combo.currentData(), {}); self.maximum_spin.setValue(entry.get("maximum_hp", 1)); self.current_spin.setValue(entry.get("current_hp", 0))
    def _save(self) -> None:
        self._result = normalize_user_confirmed_current_hp({"side": self.side_combo.currentData(), "current_hp": self.current_spin.value(), "maximum_hp": self.maximum_spin.value(), "status": "user_confirmed", "source": "user_confirmed_current_hp"}); self.accept()
