from __future__ import annotations

from copy import deepcopy
from typing import Any
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QPushButton, QVBoxLayout, QWidget
from llm.advisor_battle_state_context import normalize_user_confirmed_battle_format


class CurrentBattleFormatDialog(QDialog):
    def __init__(self, *, battle_format: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent); self.setWindowTitle("Battle Format"); self._result = None
        layout = QVBoxLayout(self); form = QFormLayout(); self.combo = QComboBox(); self.combo.addItem("Singles", "singles"); self.combo.addItem("Doubles", "doubles")
        if battle_format and battle_format.get("battle_format") == "doubles": self.combo.setCurrentIndex(1)
        form.addRow("Battle Format", self.combo); layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    @property
    def battle_format_confirmation(self) -> dict[str, Any] | None: return deepcopy(self._result)
    def _save(self) -> None:
        self._result = normalize_user_confirmed_battle_format({"battle_format": self.combo.currentData(), "source": "user_confirmed_battle_format"}); self.accept()
