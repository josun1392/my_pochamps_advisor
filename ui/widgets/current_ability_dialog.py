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
    QVBoxLayout,
    QWidget,
)

from llm.advisor_battle_state_context import normalize_user_confirmed_current_ability


ABILITY_SOURCE = "user_confirmed_current_ability"
ABILITY_STATUS = "user_confirmed"
ABILITY_SIDE_OPTIONS = (("self", "Self"), ("opponent", "Opponent"))


class CurrentAbilityDialog(QDialog):
    def __init__(
        self,
        *,
        current_abilities: dict[str, dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current Ability")
        self._current_abilities = deepcopy(current_abilities or {})
        self._result_ability: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Current ability")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("currentAbilitySummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        form = QFormLayout()
        self.side_combo = self._combo(ABILITY_SIDE_OPTIONS)
        self.ability_combo = QComboBox()
        self.ability_combo.setEditable(True)
        self.ability_combo.addItem("Unknown", "unknown")
        self.side_combo.currentIndexChanged.connect(self._load_selected_side)
        form.addRow("Side", self.side_combo)
        form.addRow("Current ability", self.ability_combo)
        layout.addLayout(form)

        hint = QLabel(
            "Records only a user-confirmed current ability identity. It does not record activation, suppression, "
            "replacement, effects, damage, RNG, post-turn state, or final turn order."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Apply")
        button_box.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._refresh_summary()
        self._load_selected_side()

    @property
    def current_ability_confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result_ability) if self._result_ability is not None else None

    def _save_and_accept(self) -> None:
        self._result_ability = normalize_user_confirmed_current_ability(
            {
                "side": str(self.side_combo.currentData()),
                "ability": self.ability_combo.currentText(),
                "status": ABILITY_STATUS,
                "source": ABILITY_SOURCE,
            }
        )
        self.accept()

    def _load_selected_side(self) -> None:
        side = str(self.side_combo.currentData())
        current = self._current_abilities.get(side)
        ability = current.get("ability") if isinstance(current, dict) else "unknown"
        self.ability_combo.setEditText(ability if isinstance(ability, str) else "unknown")

    def _refresh_summary(self) -> None:
        lines = []
        for side in ("self", "opponent"):
            current = self._current_abilities.get(side)
            if isinstance(current, dict) and isinstance(current.get("ability"), str):
                lines.append(f"{side}: {current['ability']}")
        self.summary_label.setText("\n".join(lines) if lines else "No current abilities saved.")

    @staticmethod
    def _combo(options: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        for option_id, label in options:
            combo.addItem(label, option_id)
        return combo
