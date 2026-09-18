from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SleepFreezeProgressionDialog(QDialog):
    """Capture explicit knowledge for the current runtime sleep/freeze episode."""

    def __init__(
        self,
        *,
        current_conditions: dict[str, str] | None = None,
        current_progressions: dict[str, dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sleep / Freeze progression")
        self._current_conditions = deepcopy(current_conditions or {})
        self._current_progressions = deepcopy(current_progressions or {})
        self._confirmation: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        title = QLabel("Sleep / Freeze progression")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        self.summary_label = QLabel(self._summary())
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        form = QFormLayout()
        self.side_combo = QComboBox()
        self.side_combo.addItem("Self", "self")
        self.side_combo.addItem("Opponent", "opponent")
        self.condition_label = QLabel("unknown")
        self.established_turn_spin = QSpinBox()
        self.established_turn_spin.setRange(1, 9999)
        self.prior_attempts_spin = QSpinBox()
        self.prior_attempts_spin.setRange(0, 2)
        self.sleep_duration_combo = QComboBox()
        self.sleep_duration_combo.addItem("Unknown", None)
        self.sleep_duration_combo.addItem("2", 2)
        self.sleep_duration_combo.addItem("3", 3)
        form.addRow("Side", self.side_combo)
        form.addRow("Current runtime condition", self.condition_label)
        form.addRow("Established turn", self.established_turn_spin)
        form.addRow("Prior attempts", self.prior_attempts_spin)
        form.addRow("Sleep duration", self.sleep_duration_combo)
        layout.addLayout(form)

        hint = QLabel(
            "Records only explicitly known progression for the current canonical sleep/freeze episode. "
            "The condition and episode identity come from runtime; no duration or attempt count is inferred."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Apply")
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.side_combo.currentIndexChanged.connect(self._load_side)
        self._load_side()

    @property
    def progression_confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._confirmation)

    def _load_side(self) -> None:
        side = str(self.side_combo.currentData())
        condition = self._current_conditions.get(side, "unknown")
        self.condition_label.setText(condition)
        current = self._current_progressions.get(side)
        if isinstance(current, dict):
            established = current.get("established_turn")
            attempts = current.get("prior_attempts")
            duration = current.get("sleep_duration")
            if isinstance(established, int) and not isinstance(established, bool):
                self.established_turn_spin.setValue(established)
            if isinstance(attempts, int) and not isinstance(attempts, bool):
                self.prior_attempts_spin.setValue(attempts)
            index = self.sleep_duration_combo.findData(duration)
            self.sleep_duration_combo.setCurrentIndex(index if index >= 0 else 0)
        else:
            self.established_turn_spin.setValue(1)
            self.prior_attempts_spin.setValue(0)
            self.sleep_duration_combo.setCurrentIndex(0)
        freeze = condition == "freeze"
        self.sleep_duration_combo.setDisabled(freeze)
        if freeze:
            self.sleep_duration_combo.setCurrentIndex(self.sleep_duration_combo.findData(None))

    def _save_and_accept(self) -> None:
        side = str(self.side_combo.currentData())
        condition = self._current_conditions.get(side, "unknown")
        duration = self.sleep_duration_combo.currentData()
        if condition == "freeze":
            duration = None
        self._confirmation = {
            "side": side,
            "established_turn": self.established_turn_spin.value(),
            "prior_attempts": self.prior_attempts_spin.value(),
            "sleep_duration": duration,
        }
        self.accept()

    def _summary(self) -> str:
        lines = []
        for side in ("self", "opponent"):
            row = self._current_progressions.get(side)
            if isinstance(row, dict):
                lines.append(
                    f"{side}: turn {row.get('established_turn')} | attempts {row.get('prior_attempts')} | "
                    f"duration {row.get('sleep_duration') if row.get('sleep_duration') is not None else 'unknown'}"
                )
        return "\n".join(lines) if lines else "No sleep/freeze progression confirmations saved."
