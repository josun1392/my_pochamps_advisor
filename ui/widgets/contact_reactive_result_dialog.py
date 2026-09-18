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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


_SIDE_OPTIONS = (("self", "Self"), ("opponent", "Opponent"))
_STATUS_OUTCOMES = (
    ("activation", "Activation"),
    ("no_activation", "No activation"),
    ("sleep", "Effect Spore: Sleep"),
    ("paralysis", "Effect Spore: Paralysis"),
    ("poison", "Effect Spore: Poison"),
    ("none", "Effect Spore: None"),
)
_ROUTING_OPTIONS = (
    (None, "Unknown / not confirmed"),
    ("target", "Contact hit reached the Pokémon holder"),
    ("substitute", "Contact hit reached a Substitute"),
)


def _token(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.lower()
        and " " not in value
        and "_" not in value
    )


class ContactStatusResultDialog(QDialog):
    """Explicit actual-result capture only; no contact/status mechanics live here."""

    def __init__(self, *, default_turn: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Contact status result")
        self._result: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Observed contact status result")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        self.attacker_side_combo = QComboBox()
        for value, label in _SIDE_OPTIONS:
            self.attacker_side_combo.addItem(label, value)
        self.move_id_edit = QLineEdit()
        self.move_id_edit.setPlaceholderText("e.g. tackle")
        self.turn_spin = QSpinBox()
        self.turn_spin.setRange(1, 9999)
        self.turn_spin.setValue(default_turn if isinstance(default_turn, int) and not isinstance(default_turn, bool) and default_turn > 0 else 1)
        self.target_hp_after_spin = QSpinBox()
        self.target_hp_after_spin.setRange(0, 99999)
        self.outcome_combo = QComboBox()
        for value, label in _STATUS_OUTCOMES:
            self.outcome_combo.addItem(label, value)

        form.addRow("Attacker side", self.attacker_side_combo)
        form.addRow("Observed move", self.move_id_edit)
        form.addRow("Turn", self.turn_spin)
        form.addRow("Defender HP after hit", self.target_hp_after_spin)
        form.addRow("Observed result", self.outcome_combo)
        layout.addLayout(form)

        hint = QLabel(
            "Confirm only what was actually observed. This dialog does not infer contact, defender ability, "
            "ability activation, Effect Spore RNG, or source action identity."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Confirm observed result")
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result)

    def _save_and_accept(self) -> None:
        move_id = self.move_id_edit.text().strip()
        if not _token(move_id):
            return
        self._result = {
            "attacker_side": str(self.attacker_side_combo.currentData()),
            "move_id": move_id,
            "turn_number": int(self.turn_spin.value()),
            "target_hp_after": int(self.target_hp_after_spin.value()),
            "outcome": str(self.outcome_combo.currentData()),
        }
        self.accept()


class ContactReactiveDamageResultDialog(QDialog):
    """Explicit actual-result capture only; canonical reactive damage stays runtime-owned."""

    def __init__(self, *, default_turn: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Contact reactive damage")
        self._result: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Observed contact reactive damage")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        self.attacker_side_combo = QComboBox()
        for value, label in _SIDE_OPTIONS:
            self.attacker_side_combo.addItem(label, value)
        self.move_id_edit = QLineEdit()
        self.move_id_edit.setPlaceholderText("e.g. tackle")
        self.turn_spin = QSpinBox()
        self.turn_spin.setRange(1, 9999)
        self.turn_spin.setValue(default_turn if isinstance(default_turn, int) and not isinstance(default_turn, bool) and default_turn > 0 else 1)
        self.attacker_hp_after_spin = QSpinBox()
        self.attacker_hp_after_spin.setRange(0, 99999)
        self.source_hit_damage_spin = QSpinBox()
        self.source_hit_damage_spin.setRange(0, 99999)
        self.routing_combo = QComboBox()
        for value, label in _ROUTING_OPTIONS:
            self.routing_combo.addItem(label, value)

        form.addRow("Attacker side", self.attacker_side_combo)
        form.addRow("Observed move", self.move_id_edit)
        form.addRow("Turn", self.turn_spin)
        form.addRow("Attacker HP after reactive damage", self.attacker_hp_after_spin)
        form.addRow("Actual damage dealt by contact hit", self.source_hit_damage_spin)
        form.addRow("Observed target routing", self.routing_combo)
        layout.addLayout(form)

        hint = QLabel(
            "Confirm only observed values. Unknown routing stays unknown; this dialog does not calculate "
            "Rough Skin, Iron Barbs, Rocky Helmet, stacking, or reactive KO damage."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Confirm observed result")
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result)

    def _save_and_accept(self) -> None:
        move_id = self.move_id_edit.text().strip()
        if not _token(move_id):
            return
        self._result = {
            "attacker_side": str(self.attacker_side_combo.currentData()),
            "move_id": move_id,
            "turn_number": int(self.turn_spin.value()),
            "attacker_hp_after": int(self.attacker_hp_after_spin.value()),
            "source_hit_actual_damage": int(self.source_hit_damage_spin.value()),
            "source_hit_target_routing": self.routing_combo.currentData(),
        }
        self.accept()
