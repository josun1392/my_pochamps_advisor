from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_user_confirmed_final_battle_stat


class CurrentFinalStatDialog(QDialog):
    def __init__(self, *, current_stats: dict[tuple[str, str], dict[str, Any]] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current Final Stats")
        self._current = deepcopy(current_stats or {})
        self._result: dict[str, Any] | None = None
        layout = QVBoxLayout(self); self.summary_label = QLabel(); self.summary_label.setWordWrap(True); layout.addWidget(self.summary_label)
        form = QFormLayout(); self.side_combo = QComboBox(); self.side_combo.addItem("Self", "self"); self.side_combo.addItem("Opponent", "opponent")
        self.stat_combo = QComboBox()
        for stat in ("hp", "attack", "defense", "special-attack", "special-defense", "speed"): self.stat_combo.addItem(stat, stat)
        self.value_spin = QSpinBox(); self.value_spin.setRange(1, 9999)
        self.side_combo.currentIndexChanged.connect(self._load); self.stat_combo.currentIndexChanged.connect(self._load)
        form.addRow("Side", self.side_combo); form.addRow("Final stat", self.stat_combo); form.addRow("Maximum HP / stat value", self.value_spin); layout.addLayout(form)
        layout.addWidget(QLabel("Records a user-confirmed stage-unmodified final stat. HP is maximum HP, not current HP."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons); self._refresh(); self._load()
    @property
    def current_final_stat_confirmation(self) -> dict[str, Any] | None: return deepcopy(self._result) if self._result else None
    def _refresh(self) -> None: self.summary_label.setText("\n".join(f"{side} {stat}: {entry['value']}" for (side, stat), entry in sorted(self._current.items())) or "No final stats saved.")
    def _load(self) -> None:
        entry = self._current.get((self.side_combo.currentData(), self.stat_combo.currentData()))
        self.value_spin.setValue(entry["value"] if isinstance(entry, dict) else 1)
    def _save(self) -> None:
        self._result = normalize_user_confirmed_final_battle_stat({"side": self.side_combo.currentData(), "stat": self.stat_combo.currentData(), "value": self.value_spin.value(), "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}); self.accept()
