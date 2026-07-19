from __future__ import annotations

from copy import deepcopy
from typing import Any
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget


class CurrentObservedDamageDialog(QDialog):
    def __init__(self, *, observed_damage: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent); self.setWindowTitle("Previous Direct Damage"); self._result = None
        layout=QVBoxLayout(self); form=QFormLayout(); self.damage=QLineEdit(str(observed_damage.get("damage", "")) if observed_damage else ""); self.category=QComboBox(); self.category.addItem("Physical", "physical"); self.category.addItem("Special", "special")
        if observed_damage and observed_damage.get("damage_category")=="special": self.category.setCurrentIndex(1)
        form.addRow("Damage", self.damage); form.addRow("Category", self.category); layout.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply=QPushButton("Apply"); buttons.addButton(apply,QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    @property
    def observed_damage_confirmation(self): return deepcopy(self._result)
    def _save(self):
        try: damage=int(self.damage.text())
        except ValueError: return
        if damage<=0: return
        self._result={"damage":damage,"damage_category":self.category.currentData(),"damage_kind":"direct_move_damage","source_side":"opponent","target_side":"self"}; self.accept()
