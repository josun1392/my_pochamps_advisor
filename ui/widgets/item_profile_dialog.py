from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


SUPPORTED_ITEM_OPTIONS = (
    "unknown",
    "none",
    "choice-band",
    "choice-specs",
    "life-orb",
    "muscle-band",
    "wise-glasses",
)

ITEM_LABELS = {
    "unknown": "Unknown item",
    "none": "No item",
    "choice-band": "Choice Band",
    "choice-specs": "Choice Specs",
    "life-orb": "Life Orb",
    "muscle-band": "Muscle Band",
    "wise-glasses": "Wise Glasses",
}

ITEM_NOTES = {
    "choice-band": [
        "Choice Band damage modifier is supported for physical moves.",
        "Choice lock is not connected.",
    ],
    "choice-specs": [
        "Choice Specs damage modifier is supported for special moves.",
        "Choice lock is not connected.",
    ],
    "life-orb": [
        "Life Orb damage modifier is supported.",
        "Life Orb recoil is not connected.",
    ],
    "muscle-band": [
        "Muscle Band damage modifier is supported for physical moves.",
    ],
    "wise-glasses": [
        "Wise Glasses damage modifier is supported for special moves.",
    ],
}


def default_item_profile_for_role(role_key: str) -> dict[str, Any]:
    if role_key == "opponent_active":
        return unknown_item_profile()
    return system_default_none_item_profile()


def system_default_none_item_profile() -> dict[str, Any]:
    return {
        "status": "system_default_none",
        "source": "system_default",
        "item_id": None,
        "name_en": None,
        "name_ko": None,
        "effects_scope": [],
        "damage_modifier_status": "not_applicable",
        "notes": ["No item is assumed by default."],
    }


def unknown_item_profile() -> dict[str, Any]:
    return {
        "status": "unknown",
        "source": "user_unconfirmed",
        "item_id": None,
        "name_en": None,
        "name_ko": None,
        "effects_scope": [],
        "damage_modifier_status": "not_applicable",
        "notes": ["Opponent item is unknown."],
    }


def no_item_profile() -> dict[str, Any]:
    return {
        "status": "none",
        "source": "user_confirmed",
        "item_id": None,
        "name_en": None,
        "name_ko": None,
        "effects_scope": [],
        "damage_modifier_status": "not_applicable",
        "notes": ["No item has been user-confirmed."],
    }


def user_confirmed_item_profile(item_id: str) -> dict[str, Any]:
    if item_id not in SUPPORTED_ITEM_OPTIONS or item_id in {"unknown", "none"}:
        raise ValueError(f"Unsupported v0.18 item option: {item_id}")
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": item_id,
        "name_en": ITEM_LABELS[item_id],
        "name_ko": None,
        "effects_scope": ["damage_modifier"],
        "damage_modifier_status": "applied",
        "notes": list(ITEM_NOTES[item_id]),
    }


def item_profile_from_option(option_id: str, *, role_key: str = "my_active") -> dict[str, Any]:
    if option_id == "unknown":
        return unknown_item_profile()
    if option_id == "none":
        return no_item_profile()
    if option_id in SUPPORTED_ITEM_OPTIONS:
        return user_confirmed_item_profile(option_id)
    return default_item_profile_for_role(role_key)


def option_from_item_profile(profile: dict[str, Any] | None, *, role_key: str = "my_active") -> str:
    if not isinstance(profile, dict):
        return "unknown" if role_key == "opponent_active" else "none"
    status = profile.get("status")
    if status == "unknown":
        return "unknown"
    if status in {"none", "system_default_none"}:
        return "none"
    item_id = profile.get("item_id")
    if status == "user_confirmed" and isinstance(item_id, str) and item_id in SUPPORTED_ITEM_OPTIONS:
        return item_id
    return "unknown"


def item_button_text(profile: dict[str, Any] | None, *, role_key: str = "my_active") -> str:
    effective = profile if isinstance(profile, dict) else default_item_profile_for_role(role_key)
    status = effective.get("status")
    if status == "unknown":
        return "Item?"
    if status == "none":
        return "NoItem"
    if status == "user_confirmed":
        item_id = effective.get("item_id")
        label = ITEM_LABELS.get(str(item_id), "Item")
        return label[:8]
    return "Item"


class ItemProfileDialog(QDialog):
    def __init__(
        self,
        *,
        pokemon_name: str,
        current_profile: dict[str, Any] | None = None,
        role_key: str = "my_active",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Held Item")
        self._role_key = role_key
        self._result_profile: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"{pokemon_name} held item")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        self.item_combo = QComboBox()
        for option_id in SUPPORTED_ITEM_OPTIONS:
            self.item_combo.addItem(ITEM_LABELS[option_id], option_id)
        selected = option_from_item_profile(current_profile, role_key=role_key)
        index = self.item_combo.findData(selected)
        if index >= 0:
            self.item_combo.setCurrentIndex(index)
        layout.addWidget(self.item_combo)

        hint = QLabel(
            "현재는 데미지 보정 아이템 일부만 지원합니다.\n"
            "구애 고정, 반동, 스피드, 회복, 생존 효과, KO 확률은 미지원입니다."
        )
        hint.setText(
            "지원 범위 안내: 현재 목록은 전체 포챔스 합법 아이템 목록이 아니라, "
            "데미지 계산에 연결된 일부 아이템입니다.\n"
            "일부 아이템은 Reg M-A 합법 여부가 확인되지 않았거나 실제 합법 목록과 다를 수 있습니다.\n"
            "구애 고정, 반동, 스피드, 회복, 생존 효과, KO 확률은 미지원입니다."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #52616F;")
        layout.addWidget(hint)

        button_row = QHBoxLayout()
        clear_button = QPushButton("Reset")
        clear_button.clicked.connect(self._reset_and_accept)
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
    def item_profile(self) -> dict[str, Any] | None:
        return deepcopy(self._result_profile) if self._result_profile is not None else None

    def _save_and_accept(self) -> None:
        option_id = str(self.item_combo.currentData())
        self._result_profile = item_profile_from_option(option_id, role_key=self._role_key)
        self.accept()

    def _reset_and_accept(self) -> None:
        self._result_profile = None
        self.accept()
