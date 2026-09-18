from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


_SLEEP_OPTIONS = (
    ("remained_asleep", "Remained asleep; move did not execute"),
    ("woke_and_executed", "Woke up; move executed"),
    ("executed_while_asleep", "Move executed while still asleep"),
)
_FREEZE_OPTIONS = (
    ("remained_frozen", "Remained frozen; move did not execute"),
    ("natural_thaw", "Thawed naturally; move executed"),
    ("self_thaw_move", "Self-thaw move executed"),
)


def _token(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.lower()
        and " " not in value
        and "_" not in value
    )


class SleepFreezeActionResultDialog(QDialog):
    """Capture an explicitly observed sleep/freeze action result only."""

    def __init__(
        self,
        *,
        current_conditions: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sleep / Freeze action result")
        self._current_conditions = deepcopy(current_conditions or {})
        self._confirmation: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Observed Sleep / Freeze action result")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        self.side_combo = QComboBox()
        self.side_combo.addItem("Self", "self")
        self.side_combo.addItem("Opponent", "opponent")
        self.condition_label = QLabel("unknown")
        self.move_id_edit = QLineEdit()
        self.move_id_edit.setPlaceholderText("e.g. tackle")
        self.result_combo = QComboBox()
        form.addRow("Actor side", self.side_combo)
        form.addRow("Current runtime condition", self.condition_label)
        form.addRow("Observed attempted move", self.move_id_edit)
        form.addRow("Actual result", self.result_combo)
        layout.addLayout(form)

        hint = QLabel(
            "Confirm only what actually happened. This dialog does not infer the result from duration, "
            "prior attempts, probabilities, move selection, or recommendations."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.confirm_button = QPushButton("Confirm observed result")
        buttons.addButton(self.confirm_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.side_combo.currentIndexChanged.connect(self._load_side)
        self._load_side()

    @property
    def confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._confirmation)

    def _load_side(self) -> None:
        side = str(self.side_combo.currentData())
        condition = self._current_conditions.get(side, "unknown")
        self.condition_label.setText(condition)
        self.result_combo.clear()
        options = _SLEEP_OPTIONS if condition == "sleep" else _FREEZE_OPTIONS if condition == "freeze" else ()
        for value, label in options:
            self.result_combo.addItem(label, value)
        self.confirm_button.setEnabled(bool(options))

    def _save_and_accept(self) -> None:
        move_id = self.move_id_edit.text().strip()
        result = self.result_combo.currentData()
        if not _token(move_id) or not isinstance(result, str) or not result:
            return
        self._confirmation = {
            "side": str(self.side_combo.currentData()),
            "move_id": move_id,
            "result": result,
        }
        self.accept()
