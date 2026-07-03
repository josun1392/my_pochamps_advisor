from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


FIELD_PROFILE_STATUS_CONFIRMED = "user_confirmed"
FIELD_PROFILE_SOURCE_USER_INPUT = "user_input"
FIELD_PROFILE_STATUS_UNKNOWN = "unknown"
FIELD_PROFILE_SOURCE_UNCONFIRMED = "user_unconfirmed"

WEATHER_OPTIONS = (
    ("unknown", "Unknown"),
    ("none", "None"),
    ("sun", "Sun"),
    ("rain", "Rain"),
    ("sandstorm", "Sandstorm"),
    ("snow", "Snow"),
)
TERRAIN_OPTIONS = (
    ("unknown", "Unknown"),
    ("none", "None"),
    ("electric_terrain", "Electric Terrain"),
    ("grassy_terrain", "Grassy Terrain"),
    ("misty_terrain", "Misty Terrain"),
    ("psychic_terrain", "Psychic Terrain"),
)
ROOM_OPTIONS = (
    ("unknown", "Unknown"),
    ("none", "None"),
    ("trick_room", "Trick Room"),
    ("magic_room", "Magic Room"),
    ("wonder_room", "Wonder Room"),
)
SCREEN_OPTIONS = (
    ("reflect", "Reflect"),
    ("light_screen", "Light Screen"),
    ("aurora_veil", "Aurora Veil"),
)
HAZARD_OPTIONS = (
    ("stealth_rock", "Stealth Rock"),
    ("spikes", "Spikes"),
    ("toxic_spikes", "Toxic Spikes"),
    ("sticky_web", "Sticky Web"),
)


def unknown_field_profile() -> dict[str, Any]:
    return {
        "status": FIELD_PROFILE_STATUS_UNKNOWN,
        "source": FIELD_PROFILE_SOURCE_UNCONFIRMED,
        "value": "unknown",
    }


def user_confirmed_field_profile(value: Any) -> dict[str, Any]:
    return {
        "status": FIELD_PROFILE_STATUS_CONFIRMED,
        "source": FIELD_PROFILE_SOURCE_USER_INPUT,
        "value": deepcopy(value),
    }


def default_field_profiles() -> dict[str, dict[str, Any]]:
    return {
        "weather": unknown_field_profile(),
        "terrain": unknown_field_profile(),
        "room": unknown_field_profile(),
        "screens": unknown_field_profile(),
        "hazards": unknown_field_profile(),
    }


def single_value_from_field_profile(
    profile: dict[str, Any] | None,
    *,
    allowed_values: set[str],
) -> str:
    if not isinstance(profile, dict):
        return "unknown"
    value = profile.get("value")
    if profile.get("status") != FIELD_PROFILE_STATUS_CONFIRMED or profile.get("source") != FIELD_PROFILE_SOURCE_USER_INPUT:
        return "unknown"
    if isinstance(value, str) and value in allowed_values:
        return value
    return "unknown"


def side_values_from_field_profile(
    profile: dict[str, Any] | None,
    *,
    allowed_values: set[str],
) -> dict[str, list[str]]:
    empty = {"self": [], "opponent": []}
    if not isinstance(profile, dict):
        return empty
    if profile.get("status") != FIELD_PROFILE_STATUS_CONFIRMED or profile.get("source") != FIELD_PROFILE_SOURCE_USER_INPUT:
        return empty
    value = profile.get("value")
    if not isinstance(value, dict):
        return empty
    result = {"self": [], "opponent": []}
    for side in ("self", "opponent"):
        side_value = value.get(side)
        if isinstance(side_value, list):
            result[side] = [entry for entry in side_value if isinstance(entry, str) and entry in allowed_values]
    return result


class FieldProfileDialog(QDialog):
    def __init__(
        self,
        *,
        current_profiles: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Field State")
        self._result_profiles: dict[str, dict[str, Any]] | None = None
        self._screen_checks: dict[str, dict[str, QCheckBox]] = {"self": {}, "opponent": {}}
        self._hazard_checks: dict[str, dict[str, QCheckBox]] = {"self": {}, "opponent": {}}
        self._side_modes: dict[str, QComboBox] = {}

        profiles = current_profiles if isinstance(current_profiles, dict) else {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Field state")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.weather_combo = self._combo(WEATHER_OPTIONS)
        self.terrain_combo = self._combo(TERRAIN_OPTIONS)
        self.room_combo = self._combo(ROOM_OPTIONS)
        self._set_combo_value(
            self.weather_combo,
            single_value_from_field_profile(
                profiles.get("weather"),
                allowed_values={option_id for option_id, _label in WEATHER_OPTIONS},
            ),
        )
        self._set_combo_value(
            self.terrain_combo,
            single_value_from_field_profile(
                profiles.get("terrain"),
                allowed_values={option_id for option_id, _label in TERRAIN_OPTIONS},
            ),
        )
        self._set_combo_value(
            self.room_combo,
            single_value_from_field_profile(
                profiles.get("room"),
                allowed_values={option_id for option_id, _label in ROOM_OPTIONS},
            ),
        )
        form.addRow("Weather", self.weather_combo)
        form.addRow("Terrain", self.terrain_combo)
        form.addRow("Room", self.room_combo)
        layout.addLayout(form)

        layout.addWidget(
            self._side_group(
                field_key="screens",
                title="Screens",
                options=SCREEN_OPTIONS,
                checks=self._screen_checks,
                initial_profile=profiles.get("screens"),
                allowed_values={option_id for option_id, _label in SCREEN_OPTIONS},
            )
        )
        layout.addWidget(
            self._side_group(
                field_key="hazards",
                title="Hazards",
                options=HAZARD_OPTIONS,
                checks=self._hazard_checks,
                initial_profile=profiles.get("hazards"),
                allowed_values={option_id for option_id, _label in HAZARD_OPTIONS},
            )
        )

        hint = QLabel(
            "Field entries are user-confirmed current context only. They do not set duration, expiration, "
            "post-turn state, damage precision, or full turn outcome."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        button_row = QHBoxLayout()
        reset_button = QPushButton("Reset unknown")
        reset_button.clicked.connect(self._reset_unknown)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Apply")
        button_box.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)
        button_row.addWidget(button_box)
        layout.addLayout(button_row)

    @property
    def field_profiles(self) -> dict[str, dict[str, Any]] | None:
        return deepcopy(self._result_profiles) if self._result_profiles is not None else None

    def _save_and_accept(self) -> None:
        self._result_profiles = self._build_profiles()
        self.accept()

    def _reset_unknown(self) -> None:
        self._set_combo_value(self.weather_combo, "unknown")
        self._set_combo_value(self.terrain_combo, "unknown")
        self._set_combo_value(self.room_combo, "unknown")
        for checks_by_side in (self._screen_checks, self._hazard_checks):
            for side_checks in checks_by_side.values():
                for checkbox in side_checks.values():
                    checkbox.setChecked(False)
        for mode_combo in self._side_modes.values():
            self._set_combo_value(mode_combo, "unknown")

    def _build_profiles(self) -> dict[str, dict[str, Any]]:
        return {
            "weather": self._single_profile(self.weather_combo),
            "terrain": self._single_profile(self.terrain_combo),
            "room": self._single_profile(self.room_combo),
            "screens": self._side_profile("screens", self._screen_checks),
            "hazards": self._side_profile("hazards", self._hazard_checks),
        }

    def _single_profile(self, combo: QComboBox) -> dict[str, Any]:
        value = str(combo.currentData())
        if value == "unknown":
            return unknown_field_profile()
        return user_confirmed_field_profile(value)

    def _side_values(self, checks_by_side: dict[str, dict[str, QCheckBox]]) -> dict[str, list[str]]:
        return {
            side: [
                option_id
                for option_id, checkbox in checks.items()
                if checkbox.isChecked()
            ]
            for side, checks in checks_by_side.items()
        }

    def _side_profile(self, field_key: str, checks_by_side: dict[str, dict[str, QCheckBox]]) -> dict[str, Any]:
        mode = str(self._side_modes[field_key].currentData())
        if mode == "unknown":
            return unknown_field_profile()
        if mode == "none":
            return user_confirmed_field_profile({"self": [], "opponent": []})
        return user_confirmed_field_profile(self._side_values(checks_by_side))

    def _combo(self, options: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        for option_id, label in options:
            combo.addItem(label, option_id)
        return combo

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else combo.findData("unknown"))

    def _side_group(
        self,
        *,
        field_key: str,
        title: str,
        options: tuple[tuple[str, str], ...],
        checks: dict[str, dict[str, QCheckBox]],
        initial_profile: Any,
        allowed_values: set[str],
    ) -> QGroupBox:
        group = QGroupBox(title)
        outer_layout = QVBoxLayout(group)
        mode_combo = self._combo((("unknown", "Unknown"), ("none", "None"), ("selected", "Selected")))
        mode = _side_mode_from_field_profile(initial_profile)
        self._set_combo_value(mode_combo, mode)
        self._side_modes[field_key] = mode_combo
        outer_layout.addWidget(mode_combo)

        group_layout = QHBoxLayout()
        outer_layout.addLayout(group_layout)
        initial = side_values_from_field_profile(
            initial_profile,
            allowed_values=allowed_values,
        )
        for side in ("self", "opponent"):
            side_box = QGroupBox("Self" if side == "self" else "Opponent")
            side_layout = QVBoxLayout(side_box)
            selected = set(initial.get(side, []))
            for option_id, label in options:
                checkbox = QCheckBox(label)
                checkbox.setChecked(option_id in selected)
                checkbox.toggled.connect(
                    lambda checked, combo=mode_combo: self._set_combo_value(combo, "selected") if checked else None
                )
                checks[side][option_id] = checkbox
                side_layout.addWidget(checkbox)
            group_layout.addWidget(side_box)
        return group


def _side_mode_from_field_profile(profile: Any) -> str:
    if not isinstance(profile, dict):
        return "unknown"
    if profile.get("status") != FIELD_PROFILE_STATUS_CONFIRMED or profile.get("source") != FIELD_PROFILE_SOURCE_USER_INPUT:
        return "unknown"
    value = profile.get("value")
    if not isinstance(value, dict):
        return "unknown"
    if value.get("self") == [] and value.get("opponent") == []:
        return "none"
    return "selected"
