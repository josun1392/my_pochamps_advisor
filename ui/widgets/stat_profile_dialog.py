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


def champions_neutral_final_stats(base_stats: dict[str, int] | None) -> dict[str, int] | None:
    if base_stats is None:
        return None
    stats: dict[str, int] = {}
    try:
        for key in STAT_KEYS:
            stats[key] = calc_stat_gen9(
                base=int(base_stats[BASE_STAT_KEYS[key]]),
                ev=0,
                iv=CHAMPIONS_IV,
                level=CHAMPIONS_LEVEL,
                nature_mod=1.0,
                is_hp=key == "hp",
            )
    except (KeyError, TypeError, ValueError):
        return None
    return stats


class StatProfileDialog(QDialog):
    def __init__(
        self,
        *,
        pokemon_name: str,
        current_stats: dict[str, int] | None = None,
        base_stats: dict[str, int] | None = None,
        stat_limits: dict[str, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Final Stats (Champions)")
        self._result_stats: dict[str, int] | None = None
        self._spinboxes: dict[str, QSpinBox] = {}
        self._base_final_stats = champions_neutral_final_stats(base_stats)
        self._stat_limits = stat_limits
        self._updating_spinboxes = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"{pokemon_name} 포챔스 스탯 포인트")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        normalized = validate_final_stats(current_stats, stat_limits)
        for key in STAT_KEYS:
            spinbox = QSpinBox()
            spinbox.setRange(0, CHAMPIONS_STAT_POINT_PER_STAT_CAP)
            point_value = 0
            if normalized is not None and self._base_final_stats is not None:
                point_value = max(0, min(CHAMPIONS_STAT_POINT_PER_STAT_CAP, normalized[key] - self._base_final_stats[key]))
            spinbox.setValue(point_value)
            spinbox.setKeyboardTracking(False)
            spinbox.valueChanged.connect(lambda _value, changed_key=key: self._enforce_total_cap(changed_key))
            self._spinboxes[key] = spinbox
            label = f"{STAT_LABELS[key]} SP (max {CHAMPIONS_STAT_POINT_PER_STAT_CAP})"
            form.addRow(label, spinbox)
        layout.addLayout(form)

        hint = QLabel(
            "포켓몬 챔피언스 스탯 포인트 기준: 한 능력치 최대 32 / 총합 66입니다. "
            "총합이 66을 넘으면 입력 중인 항목이 자동으로 조정됩니다. "
            "저장하면 선택한 포켓몬의 기준 최종 스탯에 입력한 포인트를 더해 계산에 사용합니다. "
            "Clear를 누르면 기본 가정으로 돌아갑니다."
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

    def _enforce_total_cap(self, changed_key: str) -> None:
        if self._updating_spinboxes:
            return
        total = sum(spinbox.value() for spinbox in self._spinboxes.values())
        if total <= CHAMPIONS_STAT_POINT_TOTAL_CAP:
            return
        overflow = total - CHAMPIONS_STAT_POINT_TOTAL_CAP
        changed_spinbox = self._spinboxes[changed_key]
        self._updating_spinboxes = True
        changed_spinbox.setValue(max(0, changed_spinbox.value() - overflow))
        self._updating_spinboxes = False

    def _save_and_accept(self) -> None:
        if self._base_final_stats is None:
            self._result_stats = {key: spinbox.value() for key, spinbox in self._spinboxes.items()}
        else:
            self._result_stats = {
                key: self._base_final_stats[key] + spinbox.value()
                for key, spinbox in self._spinboxes.items()
            }
        self.accept()

    def _clear_and_accept(self) -> None:
        self._result_stats = None
        self.accept()
