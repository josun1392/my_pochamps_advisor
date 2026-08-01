from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_user_confirmed_current_field_state


class CurrentFieldStateDialog(QDialog):
    def __init__(self, *, current_field: dict[str, Any] | None = None, grounded_context: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent); self.setWindowTitle("Current Field State")
        self._current = deepcopy(current_field) if isinstance(current_field, dict) else None
        self._grounded_current = deepcopy(grounded_context) if isinstance(grounded_context, dict) else {}
        self._result: dict[str, Any] | None = None
        self._grounded_result: dict[str, Any] | None = None
        layout = QVBoxLayout(self); self.summary_label = QLabel(); self.summary_label.setWordWrap(True); layout.addWidget(self.summary_label)
        form = QFormLayout(); self.weather = self._combo(("none", "sun", "rain", "sandstorm", "snow")); self.terrain = self._combo(("none", "electric", "grassy", "psychic", "misty")); self.self_grounded = self._combo(("unknown", "known_grounded", "known_ungrounded")); self.opponent_grounded = self._combo(("unknown", "known_grounded", "known_ungrounded")); form.addRow("Weather", self.weather); form.addRow("Terrain", self.terrain); form.addRow("Self grounded", self.self_grounded); form.addRow("Opponent grounded", self.opponent_grounded); layout.addLayout(form)
        self.global_boxes = {effect: QCheckBox(effect) for effect in ("trick-room", "gravity")}
        self.self_boxes = {effect: QCheckBox(f"self {effect}") for effect in ("reflect", "light-screen", "aurora-veil", "tailwind")}
        self.opponent_boxes = {effect: QCheckBox(f"opponent {effect}") for effect in ("reflect", "light-screen", "aurora-veil", "tailwind")}
        for box in (*self.global_boxes.values(), *self.self_boxes.values(), *self.opponent_boxes.values()): layout.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel); apply = QPushButton("Apply"); buttons.addButton(apply, QDialogButtonBox.ButtonRole.AcceptRole); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self._load()

    @property
    def current_field_state_confirmation(self) -> dict[str, Any] | None: return deepcopy(self._result) if self._result else None
    @property
    def grounded_context_confirmation(self) -> dict[str, Any] | None: return deepcopy(self._grounded_result) if self._grounded_result else None
    def _combo(self, values: tuple[str, ...]) -> QComboBox:
        combo = QComboBox(); [combo.addItem(value, value) for value in values]; return combo
    def _load(self) -> None:
        current = self._current or {"weather": "none", "terrain": "none", "global_effects": [], "side_effects": []}
        self.weather.setCurrentText(current.get("weather", "none")); self.terrain.setCurrentText(current.get("terrain", "none"))
        self.self_grounded.setCurrentText(self._grounded_current.get("self", {}).get("status", "unknown")); self.opponent_grounded.setCurrentText(self._grounded_current.get("opponent", {}).get("status", "unknown"))
        globals_ = set(current.get("global_effects", [])); sides = {(value.get("side"), value.get("effect")) for value in current.get("side_effects", []) if isinstance(value, dict)}
        for effect, box in self.global_boxes.items(): box.setChecked(effect in globals_)
        for effect, box in self.self_boxes.items(): box.setChecked(("self", effect) in sides)
        for effect, box in self.opponent_boxes.items(): box.setChecked(("opponent", effect) in sides)
        self.summary_label.setText("Field snapshot saved." if self._current else "No field snapshot saved.")
    def _save(self) -> None:
        side_effects = ([{"side": "self", "effect": effect} for effect, box in self.self_boxes.items() if box.isChecked()] + [{"side": "opponent", "effect": effect} for effect, box in self.opponent_boxes.items() if box.isChecked()])
        self._result = normalize_user_confirmed_current_field_state({"weather": self.weather.currentData(), "terrain": self.terrain.currentData(), "global_effects": [effect for effect, box in self.global_boxes.items() if box.isChecked()], "side_effects": side_effects, "status": "user_confirmed", "source": "user_confirmed_current_field_state"}); self._grounded_result = {side: {"status": value, "provenance": "unknown" if value == "unknown" else "user_confirmed_current"} for side, value in (("self", self.self_grounded.currentData()), ("opponent", self.opponent_grounded.currentData()))}; self.accept()
