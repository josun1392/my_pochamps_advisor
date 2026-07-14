from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_user_confirmed_current_stat_stage


class CurrentStatStageDialog(QDialog):
    def __init__(self, *, current_stages: dict[tuple[str, str], dict[str, Any]] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current Stat Stages")
        self._current_stages = deepcopy(current_stages or {})
        self._result_stage: dict[str, Any] | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Current stat stage"))
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        form = QFormLayout()
        self.side_combo = QComboBox()
        self.side_combo.addItem("Self", "self")
        self.side_combo.addItem("Opponent", "opponent")
        self.stat_combo = QComboBox()
        for stat in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion"):
            self.stat_combo.addItem(stat, stat)
        self.stage_spin = QSpinBox()
        self.stage_spin.setRange(-6, 6)
        self.side_combo.currentIndexChanged.connect(self._load_selected)
        self.stat_combo.currentIndexChanged.connect(self._load_selected)
        form.addRow("Side", self.side_combo)
        form.addRow("Stat", self.stat_combo)
        form.addRow("Stage", self.stage_spin)
        layout.addLayout(form)
        hint = QLabel("Records only a user-confirmed current stage, not its cause, exact stat, damage, HP, or final order.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Apply")
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_summary()
        self._load_selected()

    @property
    def current_stat_stage_confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result_stage) if self._result_stage is not None else None

    def _load_selected(self) -> None:
        current = self._current_stages.get((str(self.side_combo.currentData()), str(self.stat_combo.currentData())))
        self.stage_spin.setValue(int(current.get("stage", 0)) if isinstance(current, dict) else 0)

    def _refresh_summary(self) -> None:
        lines = [f"{side} {stat}: {stage['stage']:+d}" for (side, stat), stage in sorted(self._current_stages.items())]
        self.summary_label.setText("\n".join(lines) if lines else "No current stat stages saved.")

    def _save_and_accept(self) -> None:
        self._result_stage = normalize_user_confirmed_current_stat_stage({
            "side": str(self.side_combo.currentData()), "stat": str(self.stat_combo.currentData()),
            "stage": self.stage_spin.value(), "status": "user_confirmed", "source": "user_confirmed_current_stat_stage",
        })
        self.accept()
