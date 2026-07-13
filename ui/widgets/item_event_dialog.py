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
    QListWidget,
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
        self._draft_events: list[dict[str, Any]] = deepcopy(current_events or [])
        self._selected_event_index: int | None = None
        self._draft_reset = False
        self._has_list_mutation = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Item event")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        self.event_list = QListWidget()
        self.event_list.setObjectName("itemEventSummaryList")
        self.event_list.setToolTip("Current user-confirmed observed item events for this session.")
        self.event_list.currentRowChanged.connect(self._load_selected_event)
        layout.addWidget(self.event_list)

        list_actions = QHBoxLayout()
        add_button = QPushButton("Add event")
        add_button.clicked.connect(self._start_new_event)
        self.delete_button = QPushButton("Delete selected")
        self.delete_button.clicked.connect(self._delete_selected_event)
        list_actions.addWidget(add_button)
        list_actions.addWidget(self.delete_button)
        list_actions.addStretch(1)
        layout.addLayout(list_actions)

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

        self._refresh_event_list()
        self._load_initial_event(self._draft_events)

    @property
    def item_event_confirmations(self) -> list[dict[str, Any]] | None:
        return deepcopy(self._result_events) if self._result_events is not None else None

    def _save_and_accept(self) -> None:
        if self._draft_reset:
            self._result_events = []
        elif self._selected_event_index is None and self._has_list_mutation:
            self._result_events = deepcopy(self._draft_events)
        else:
            event = self._build_event()
            if self._selected_event_index is None:
                self._draft_events.append(event)
            else:
                self._draft_events[self._selected_event_index] = event
                self._remove_duplicates_for_selected_event(event)
            self._result_events = deepcopy(self._draft_events)
        self.accept()

    def _remove_duplicates_for_selected_event(self, event: dict[str, Any]) -> None:
        """Keep an edited event when its new identity matches another draft entry."""
        if self._selected_event_index is None:
            return
        identity = self._event_identity(event)
        selected_index = self._selected_event_index
        self._draft_events = [
            candidate
            for index, candidate in enumerate(self._draft_events)
            if index == selected_index or self._event_identity(candidate) != identity
        ]

    @staticmethod
    def _event_identity(event: dict[str, Any]) -> tuple[object, object, object, object]:
        return (event.get("side"), event.get("item"), event.get("event_type"), event.get("turn"))

    def _reset_draft(self) -> None:
        self._draft_reset = True
        self._has_list_mutation = True
        self._draft_events = []
        self._selected_event_index = None
        self._refresh_event_list()
        self._set_combo_value(self.side_combo, "opponent")
        self._set_combo_value(self.event_type_combo, "item_activation_observed")
        self.item_combo.setEditText("")
        self.turn_spin.setValue(0)
        self.note_edit.clear()

    def _start_new_event(self) -> None:
        self._draft_reset = False
        self._has_list_mutation = False
        self._selected_event_index = None
        self.event_list.clearSelection()
        self._set_combo_value(self.side_combo, "opponent")
        self._set_combo_value(self.event_type_combo, "item_activation_observed")
        self.item_combo.setEditText("")
        self.turn_spin.setValue(0)
        self.note_edit.clear()

    def _delete_selected_event(self) -> None:
        if self._selected_event_index is None:
            return
        deleted_index = self._selected_event_index
        del self._draft_events[deleted_index]
        self._selected_event_index = None
        self._draft_reset = not self._draft_events
        self._has_list_mutation = True
        self._refresh_event_list()
        self._set_combo_value(self.side_combo, "opponent")
        self._set_combo_value(self.event_type_combo, "item_activation_observed")
        self.item_combo.setEditText("")
        self.turn_spin.setValue(0)
        self.note_edit.clear()

    def _refresh_event_list(self) -> None:
        self.event_list.blockSignals(True)
        self.event_list.clear()
        for event in self._draft_events:
            self.event_list.addItem(self._event_summary(event))
        self.event_list.blockSignals(False)
        self.delete_button.setEnabled(bool(self._draft_events))

    @staticmethod
    def _event_summary(event: dict[str, Any]) -> str:
        side = str(event.get("side", "unknown"))
        item = str(event.get("item", "unknown"))
        event_type = str(event.get("event_type", "unknown"))
        turn = event.get("turn")
        turn_text = f" | Turn {turn}" if isinstance(turn, int) and turn > 0 else ""
        note = event.get("note")
        note_text = f" | {note}" if isinstance(note, str) and note.strip() else ""
        return f"{side}: {item} | {event_type}{turn_text}{note_text}"

    def _load_selected_event(self, index: int) -> None:
        if not 0 <= index < len(self._draft_events):
            self._selected_event_index = None
            return
        self._draft_reset = False
        self._has_list_mutation = False
        self._selected_event_index = index
        event = self._draft_events[index]
        self._set_combo_value(self.side_combo, str(event.get("side", "opponent")))
        self._set_combo_value(self.event_type_combo, str(event.get("event_type", "item_activation_observed")))
        self.item_combo.setEditText(str(event.get("item", "")))
        turn = event.get("turn")
        self.turn_spin.setValue(turn if isinstance(turn, int) and not isinstance(turn, bool) and turn > 0 else 0)
        note = event.get("note")
        self.note_edit.setPlainText(note if isinstance(note, str) else "")

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
        self._selected_event_index = len(current_events) - 1
        self.event_list.setCurrentRow(self._selected_event_index)

    def _combo(self, options: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        for option_id, label in options:
            combo.addItem(label, option_id)
        return combo

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
