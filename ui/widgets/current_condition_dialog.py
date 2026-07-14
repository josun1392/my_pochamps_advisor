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

from llm.advisor_battle_state_context import normalize_user_confirmed_current_condition


CONDITION_SOURCE = "user_confirmed_current_condition"
CONDITION_STATUS = "user_confirmed"
CONDITION_SIDE_OPTIONS = (("self", "Self"), ("opponent", "Opponent"))
CONDITION_TYPE_OPTIONS = (
    ("burn", "Burn"),
    ("poison", "Poison"),
    ("toxic", "Toxic"),
    ("paralysis", "Paralysis"),
    ("sleep", "Sleep"),
    ("freeze", "Freeze"),
    ("none", "None"),
    ("unknown", "Unknown"),
)


class CurrentConditionDialog(QDialog):
    def __init__(
        self,
        *,
        current_conditions: dict[str, dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current Condition")
        self._current_conditions = deepcopy(current_conditions or {})
        self._result_condition: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Current condition")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("currentConditionSummary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        form = QFormLayout()
        self.side_combo = self._combo(CONDITION_SIDE_OPTIONS)
        self.condition_type_combo = self._combo(CONDITION_TYPE_OPTIONS)
        self.side_combo.currentIndexChanged.connect(self._load_selected_side)
        form.addRow("Side", self.side_combo)
        form.addRow("Current condition", self.condition_type_combo)
        layout.addLayout(form)

        hint = QLabel(
            "Records only a user-confirmed current major condition. It does not record application events, "
            "damage, duration, RNG, post-turn state, or final turn order."
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
    def current_condition_confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result_condition) if self._result_condition is not None else None

    def _save_and_accept(self) -> None:
        self._result_condition = normalize_user_confirmed_current_condition(
            {
                "side": str(self.side_combo.currentData()),
                "condition_type": str(self.condition_type_combo.currentData()),
                "status": CONDITION_STATUS,
                "source": CONDITION_SOURCE,
            }
        )
        self.accept()

    def _load_selected_side(self) -> None:
        side = str(self.side_combo.currentData())
        current = self._current_conditions.get(side)
        condition_type = current.get("condition_type") if isinstance(current, dict) else "unknown"
        index = self.condition_type_combo.findData(condition_type)
        self.condition_type_combo.setCurrentIndex(index if index >= 0 else self.condition_type_combo.findData("unknown"))

    def _refresh_summary(self) -> None:
        lines = []
        for side in ("self", "opponent"):
            current = self._current_conditions.get(side)
            if isinstance(current, dict) and isinstance(current.get("condition_type"), str):
                lines.append(f"{side}: {current['condition_type']}")
        self.summary_label.setText("\n".join(lines) if lines else "No current conditions saved.")

    @staticmethod
    def _combo(options: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        for option_id, label in options:
            combo.addItem(label, option_id)
        return combo
