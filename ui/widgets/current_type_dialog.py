from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from llm.advisor_battle_state_context import normalize_current_type_authority


class CurrentTypeDialog(QDialog):
    """Explicit current typing input; repository species types are never shown as a default."""

    def __init__(self, *, current_types: dict[str, dict[str, Any]] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Current Type")
        self._current_types = deepcopy(current_types or {})
        self._result_type: dict[str, Any] | None = None
        layout = QVBoxLayout(self)
        title = QLabel("Current type")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        form = QFormLayout()
        self.side_combo = QComboBox()
        self.side_combo.addItem("Self", "self")
        self.side_combo.addItem("Opponent", "opponent")
        self.state_combo = QComboBox()
        self.state_combo.addItem("Unknown", "unknown")
        self.state_combo.addItem("Known exact type(s)", "known")
        self.primary_type_edit = QLineEdit()
        self.secondary_type_edit = QLineEdit()
        self.secondary_type_edit.setPlaceholderText("Optional second type")
        form.addRow("Side", self.side_combo)
        form.addRow("State", self.state_combo)
        form.addRow("Type 1", self.primary_type_edit)
        form.addRow("Type 2", self.secondary_type_edit)
        layout.addLayout(form)
        hint = QLabel("Use Unknown unless the current type is explicitly confirmed. Species/base type is not used as a fallback; this does not resolve type effects or immunity.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = QPushButton("Apply")
        buttons.addButton(apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.side_combo.currentIndexChanged.connect(self._load_selected_side)
        self.state_combo.currentIndexChanged.connect(self._sync_state)
        self._refresh_summary()
        self._load_selected_side()

    @property
    def current_type_confirmation(self) -> dict[str, Any] | None:
        return deepcopy(self._result_type) if self._result_type is not None else None

    def _save_and_accept(self) -> None:
        side = str(self.side_combo.currentData())
        if self.state_combo.currentData() == "unknown":
            candidate = {"side": side, "state": "unknown", "status": "unknown", "source": "unknown", "authority_provenance": "unknown"}
        else:
            types = [self.primary_type_edit.text()]
            if self.secondary_type_edit.text().strip():
                types.append(self.secondary_type_edit.text())
            candidate = {"side": side, "state": "known", "types": types, "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current"}
        self._result_type = normalize_current_type_authority(candidate)
        self.accept()

    def _load_selected_side(self) -> None:
        current = self._current_types.get(str(self.side_combo.currentData()))
        state = current.get("state") if isinstance(current, dict) else "unknown"
        self.state_combo.setCurrentIndex(0 if state != "known" else 1)
        types = current.get("types") if isinstance(current, dict) else []
        self.primary_type_edit.setText(types[0] if isinstance(types, list) and types else "")
        self.secondary_type_edit.setText(types[1] if isinstance(types, list) and len(types) > 1 else "")
        self._sync_state()

    def _sync_state(self) -> None:
        known = self.state_combo.currentData() == "known"
        self.primary_type_edit.setEnabled(known)
        self.secondary_type_edit.setEnabled(known)

    def _refresh_summary(self) -> None:
        lines = []
        for side in ("self", "opponent"):
            entry = self._current_types.get(side)
            if not isinstance(entry, dict):
                continue
            types = entry.get("types")
            value = "/".join(types) if entry.get("state") == "known" and isinstance(types, list) else "unknown"
            lines.append(f"{side}: {value}")
        self.summary_label.setText("\n".join(lines) if lines else "No current types saved.")
