from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from llm.advisor_battle_state_context import (
    EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES,
    validate_explicit_user_item_event_confirmation,
)


ITEM_EVENT_SOURCE = "explicit_user_event_confirmation"
ITEM_EVENT_STATUS = "user_confirmed"
ITEM_EVENT_SIDE_OPTIONS = (("self", "Self"), ("opponent", "Opponent"))
ITEM_EVENT_ITEM_OPTIONS = (
    "focus-sash",
    "quick-claw",
    "sitrus-berry",
    "yache-berry",
    "leftovers",
    "choice-scarf",
)
ITEM_EVENT_TYPE_LABELS = {
    "item_activation_observed": "Activation observed",
    "item_consumption_observed": "Consumption observed",
    "item_recovery_observed": "Recovery observed",
    "item_prevention_observed": "Prevention observed",
    "item_reveal_observed": "Reveal observed",
}


class ItemEventDialog(QDialog):
    def __init__(
        self,
        *,
        current_events: list[dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Item Event")
        self._result_events: list[dict[str, Any]] | None = None
        self._draft_reset = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Item event")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.side_combo = self._combo(ITEM_EVENT_SIDE_OPTIONS)
        self.item_combo = QComboBox()
        self.item_combo.setEditable(True)
        for item_id in ITEM_EVENT_ITEM_OPTIONS:
            self.item_combo.addItem(item_id, item_id)
        self.event_type_combo = self._combo(
            tuple(
                (event_type, ITEM_EVENT_TYPE_LABELS.get(event_type, event_type))
                for event_type in sorted(EXPLICIT_USER_ITEM_EVENT_ALLOWED_EVENT_TYPES)
            )
        )
        self.turn_spin = QSpinBox()
        self.turn_spin.setRange(0, 999)
        self.turn_spin.setSpecialValueText("")
        self.turn_spin.setToolTip("Optional turn number. Blank means unspecified.")
        self.note_edit = QTextEdit()
        self.note_edit.setFixedHeight(72)

        form.addRow("Side", self.side_combo)
        form.addRow("Item", self.item_combo)
        form.addRow("Event type", self.event_type_combo)
        form.addRow("Turn", self.turn_spin)
        form.addRow("Note", self.note_edit)
        layout.addLayout(form)

        hint = QLabel(
            "Records only a user-confirmed observed item event. It does not calculate "
            "resolved effects, exact HP, damage, RNG, or turn order."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        button_row = QHBoxLayout()
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self._reset_draft)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Apply")
        button_box.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)
        button_row.addWidget(button_box)
        layout.addLayout(button_row)

        self._load_initial_event(current_events)

    @property
    def item_event_confirmations(self) -> list[dict[str, Any]] | None:
        return deepcopy(self._result_events) if self._result_events is not None else None

    def _save_and_accept(self) -> None:
        self._result_events = [] if self._draft_reset else [self._build_event()]
        self.accept()

    def _reset_draft(self) -> None:
        self._draft_reset = True
        self._set_combo_value(self.side_combo, "opponent")
        self._set_combo_value(self.event_type_combo, "item_activation_observed")
        self.item_combo.setEditText("")
        self.turn_spin.setValue(0)
        self.note_edit.clear()

    def _build_event(self) -> dict[str, Any]:
        self._draft_reset = False
        event = {
            "side": str(self.side_combo.currentData()),
            "item": self.item_combo.currentText().strip(),
            "event_type": str(self.event_type_combo.currentData()),
            "status": ITEM_EVENT_STATUS,
            "source": ITEM_EVENT_SOURCE,
            "turn": self.turn_spin.value() or None,
            "note": self.note_edit.toPlainText().strip() or None,
        }
        return validate_explicit_user_item_event_confirmation(event)

    def _load_initial_event(self, current_events: list[dict[str, Any]] | None) -> None:
        if not current_events:
            self._set_combo_value(self.side_combo, "opponent")
            self._set_combo_value(self.event_type_combo, "item_activation_observed")
            self.turn_spin.setValue(0)
            return
        event = current_events[-1]
        if not isinstance(event, dict):
            return
        self._set_combo_value(self.side_combo, str(event.get("side", "opponent")))
        self._set_combo_value(self.event_type_combo, str(event.get("event_type", "item_activation_observed")))
        item = event.get("item")
        if isinstance(item, str):
            self.item_combo.setEditText(item)
        turn = event.get("turn")
        if isinstance(turn, int) and not isinstance(turn, bool) and turn > 0:
            self.turn_spin.setValue(turn)
        note = event.get("note")
        if isinstance(note, str):
            self.note_edit.setPlainText(note)

    def _combo(self, options: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        for option_id, label in options:
            combo.addItem(label, option_id)
        return combo

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
