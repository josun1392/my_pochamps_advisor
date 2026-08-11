from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget


OPTIONS = (("모름", "unknown"), ("가능", "permitted"), ("불가능", "blocked"))


class SwitchPermissionDialog(QDialog):
    """Pure UI choice: only Apply returns a user-originated capture value."""
    def __init__(self, *, permission: str = "unknown", parent: QWidget | None = None) -> None:
        super().__init__(parent); self.setWindowTitle("교체 가능 여부"); self._result: str | None = None
        layout = QVBoxLayout(self); layout.addWidget(QLabel("현재 포켓몬의 교체 가능 여부"))
        form = QFormLayout(); self.combo = QComboBox()
        for label, value in OPTIONS: self.combo.addItem(label, value)
        index = self.combo.findData(permission if permission in {"unknown", "permitted", "blocked"} else "unknown")
        self.combo.setCurrentIndex(index if index >= 0 else 0); form.addRow("교체 가능 여부", self.combo); layout.addLayout(form)
        hint = QLabel("현재 전투 상태에 대해 직접 확인한 사실만 기록합니다."); hint.setWordWrap(True); layout.addWidget(hint)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("적용"); box.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); box.accepted.connect(self._accept); box.rejected.connect(self.reject); layout.addWidget(box)

    @property
    def permission(self) -> str | None: return self._result
    def _accept(self) -> None: self._result = str(self.combo.currentData()); self.accept()
