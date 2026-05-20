from __future__ import annotations

from typing import Any

from advisor.damage.stats import calc_stat_gen9
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
CHAMPIONS_STAT_POINT_TOTAL_CAP = 66
CHAMPIONS_STAT_POINT_PER_STAT_CAP = 32
CHAMPIONS_LEVEL = 50
CHAMPIONS_IV = 31
STAT_LABELS = {
    "hp": "HP",
    "atk": "Atk",
    "def": "Def",
    "spa": "SpA",
    "spd": "SpD",
    "spe": "Spe",
}
BASE_STAT_KEYS = {
    "hp": "hp",
    "atk": "attack",
    "def": "defense",
    "spa": "special-attack",
    "spd": "special-defense",
    "spe": "speed",
}


def validate_final_stats(
    raw_stats: dict[str, Any] | None,
    stat_limits: dict[str, int] | None = None,
) -> dict[str, int] | None:
    """Return normalized final stats only when all six positive integer stats exist."""
    if raw_stats is None:
        return None
    stats: dict[str, int] = {}
    for key in STAT_KEYS:
        value = raw_stats.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return None
        if stat_limits is not None and value > stat_limits[key]:
            return None
        stats[key] = value
    return stats


def champions_final_stat_limits(base_stats: dict[str, int] | None) -> dict[str, int] | None:
    """Return Pokemon Champions final-stat upper bounds for a level 50 Pokemon.

    Champions stat points are direct stat additions: max 32 in one stat and
    66 total. Non-HP limits include a beneficial nature so legitimate final
    stats are not rejected before nature input exists.
    """
    if base_stats is None:
        return None
    limits: dict[str, int] = {}
    try:
        for key in STAT_KEYS:
            base = int(base_stats[BASE_STAT_KEYS[key]])
            is_hp = key == "hp"
            neutral = calc_stat_gen9(
                base=base,
                ev=0,
                iv=CHAMPIONS_IV,
                level=CHAMPIONS_LEVEL,
                nature_mod=1.0,
                is_hp=is_hp,
            )
            boosted = neutral + CHAMPIONS_STAT_POINT_PER_STAT_CAP
            if not is_hp:
                boosted = (boosted * 11) // 10
            limits[key] = boosted
    except (KeyError, TypeError, ValueError):
        return None
    return limits


class StatProfileDialog(QDialog):
    def __init__(
        self,
        *,
        pokemon_name: str,
        current_stats: dict[str, int] | None = None,
        stat_limits: dict[str, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Final Stats (Champions)")
        self._result_stats: dict[str, int] | None = None
        self._spinboxes: dict[str, QSpinBox] = {}
        self._stat_limits = stat_limits

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"{pokemon_name} final stats")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        normalized = validate_final_stats(current_stats, stat_limits)
        for key in STAT_KEYS:
            spinbox = QSpinBox()
            limit = stat_limits[key] if stat_limits is not None else 999
            spinbox.setRange(1, limit)
            spinbox.setValue(normalized[key] if normalized is not None else 1)
            spinbox.setKeyboardTracking(False)
            self._spinboxes[key] = spinbox
            label = STAT_LABELS[key]
            if stat_limits is not None:
                label = f"{label} (max {limit})"
            form.addRow(label, spinbox)
        layout.addLayout(form)

        hint = QLabel(
            "Pokemon Champions Stat Points: max 32 per stat / 66 total, not Gen 9 252/510 EVs. "
            "These fields are final stats, capped by the selected Pokemon's Champions limits. "
            "Total allocation is shown as the rules limit; exact nature/SP allocation validation is not connected yet. "
            "Clear returns to default assumptions."
        )
        hint.setWordWrap(True)
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
