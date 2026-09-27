from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_user_confirmed_current_hp


class _ExactHPInput(QLineEdit):
    """Blank until an exact value is supplied; setValue retains UI test compatibility."""

    def __init__(self, minimum: int) -> None:
        super().__init__()
        self.setValidator(QIntValidator(minimum, 9999, self))
        self.setPlaceholderText("미입력")

    def setValue(self, value: int) -> None:
        self.setText(str(value))


class CurrentHPDialog(QDialog):
    """Explicit paired active HP capture that retains the legacy single-side result."""

    def __init__(self, *, current_hp: dict[str, dict[str, Any]] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current HP")
        self._current, self._result, self._results = deepcopy(current_hp or {}), None, []
        layout = QVBoxLayout(self)
        self.summary_label = QLabel(); layout.addWidget(self.summary_label)
        self.confirm_self, self.confirm_opponent = QCheckBox("Confirm self"), QCheckBox("Confirm opponent")
        self.self_current_spin, self.self_maximum_spin = self._spin_pair()
        self.opponent_current_spin, self.opponent_maximum_spin = self._spin_pair()
        # Compatibility for callers that use the original single-side controls.
        self.current_spin, self.maximum_spin = self.self_current_spin, self.self_maximum_spin
        layout.addWidget(self._side_group("Self", self.confirm_self, self.self_current_spin, self.self_maximum_spin))
        layout.addWidget(self._side_group("Opponent", self.confirm_opponent, self.opponent_current_spin, self.opponent_maximum_spin))
        layout.addWidget(QLabel("Records exact user-confirmed current and maximum HP; visible percent is not converted. Unticked sides are unchanged."))
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #B42318;")
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self._load(); self._refresh()

    @staticmethod
    def _spin_pair() -> tuple[_ExactHPInput, _ExactHPInput]:
        return _ExactHPInput(0), _ExactHPInput(1)

    @staticmethod
    def _side_group(title: str, confirm: QCheckBox, current: _ExactHPInput, maximum: _ExactHPInput) -> QGroupBox:
        group = QGroupBox(title); form = QFormLayout(group); form.addRow(confirm); form.addRow("Current HP", current); form.addRow("Maximum HP", maximum); return group

    @property
    def current_hp_confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result) if self._result else None

    @property
    def current_hp_confirmations(self) -> list[dict[str, Any]]:
        return deepcopy(self._results)

    def _refresh(self) -> None:
        self.summary_label.setText("\n".join(f"{side}: {entry['current_hp']}/{entry['maximum_hp']}" for side, entry in sorted(self._current.items())) or "No exact HP saved.")

    def _load(self) -> None:
        for side, confirm, current, maximum in (
            ("self", self.confirm_self, self.self_current_spin, self.self_maximum_spin),
            ("opponent", self.confirm_opponent, self.opponent_current_spin, self.opponent_maximum_spin),
        ):
            entry = self._current.get(side, {})
            if "maximum_hp" in entry:
                maximum.setValue(entry["maximum_hp"])
            if "current_hp" in entry:
                current.setValue(entry["current_hp"])
            confirm.setChecked(side in self._current)

    def _save(self) -> None:
        self.error_label.clear()
        results = []
        for side, confirm, current, maximum in (
            ("self", self.confirm_self, self.self_current_spin, self.self_maximum_spin),
            ("opponent", self.confirm_opponent, self.opponent_current_spin, self.opponent_maximum_spin),
        ):
            if confirm.isChecked():
                current_text, maximum_text = current.text().strip(), maximum.text().strip()
                if not current_text or not maximum_text:
                    self.error_label.setText(f"{side}: 현재 HP와 최대 HP를 모두 입력하세요.")
                    return
                try:
                    results.append(normalize_user_confirmed_current_hp({"side": side, "current_hp": int(current_text), "maximum_hp": int(maximum_text), "status": "user_confirmed", "source": "user_confirmed_current_hp"}))
                except ValueError:
                    self.error_label.setText(f"{side}: HP는 0 이상이며 최대 HP를 넘을 수 없습니다.")
                    return
        self._results = results
        self._result = next((entry for entry in results if entry["side"] == "self"), results[0] if results else None)
        if results:
            self.accept()
