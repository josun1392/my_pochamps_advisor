from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
STAT_LABELS = {
    "hp": "HP",
    "atk": "Atk",
    "def": "Def",
    "spa": "SpA",
    "spd": "SpD",
    "spe": "Spe",
}


def validate_final_stats(raw_stats: dict[str, Any] | None) -> dict[str, int] | None:
    """Return normalized final stats only when all six positive integer stats exist."""
    if raw_stats is None:
        return None
    stats: dict[str, int] = {}
    for key in STAT_KEYS:
        value = raw_stats.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return None
        stats[key] = value
    return stats


class StatProfileDialog(QDialog):
    def __init__(
        self,
        *,
        pokemon_name: str,
        current_stats: dict[str, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Final Stats")
        self._result_stats: dict[str, int] | None = None
        self._spinboxes: dict[str, QSpinBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"{pokemon_name} final stats")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        normalized = validate_final_stats(current_stats)
        for key in STAT_KEYS:
            spinbox = QSpinBox()
            spinbox.setRange(1, 999)
            spinbox.setValue(normalized[key] if normalized is not None else 1)
            spinbox.setKeyboardTracking(False)
            self._spinboxes[key] = spinbox
            form.addRow(STAT_LABELS[key], spinbox)
        layout.addLayout(form)

        hint = QLabel("All six stats are required. Clear returns to default assumptions.")
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        button_row = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._clear_and_accept)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        button_row.addWidget(button_box)
        layout.addLayout(button_row)

    @property
    def final_stats(self) -> dict[str, int] | None:
        return self._result_stats

    def _save_and_accept(self) -> None:
        self._result_stats = {key: spinbox.value() for key, spinbox in self._spinboxes.items()}
        self.accept()

    def _clear_and_accept(self) -> None:
        self._result_stats = None
        self.accept()
