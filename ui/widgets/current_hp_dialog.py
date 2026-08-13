from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_user_confirmed_current_hp


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
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self._load(); self._refresh()

    @staticmethod
    def _spin_pair() -> tuple[QSpinBox, QSpinBox]:
        current, maximum = QSpinBox(), QSpinBox()
        for spin in (current, maximum): spin.setRange(0, 9999)
        maximum.setMinimum(1)
        return current, maximum

    @staticmethod
    def _side_group(title: str, confirm: QCheckBox, current: QSpinBox, maximum: QSpinBox) -> QGroupBox:
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
            maximum.setValue(entry.get("maximum_hp", 1)); current.setValue(entry.get("current_hp", 0))
            confirm.setChecked(side in self._current)

    def _save(self) -> None:
        results = []
        for side, confirm, current, maximum in (
            ("self", self.confirm_self, self.self_current_spin, self.self_maximum_spin),
            ("opponent", self.confirm_opponent, self.opponent_current_spin, self.opponent_maximum_spin),
        ):
            if confirm.isChecked():
                results.append(normalize_user_confirmed_current_hp({"side": side, "current_hp": current.value(), "maximum_hp": maximum.value(), "status": "user_confirmed", "source": "user_confirmed_current_hp"}))
        self._results = results
        self._result = next((entry for entry in results if entry["side"] == "self"), results[0] if results else None)
        if results:
            self.accept()
