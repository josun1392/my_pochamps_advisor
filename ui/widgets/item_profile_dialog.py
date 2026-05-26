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

LEGAL_BUT_NOT_MODELED = "legal_but_not_modeled"
LEGAL_AND_DAMAGE_SUPPORTED = "legal_and_damage_supported"
DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL = "damage_supported_but_not_champions_legal"

DAMAGE_TEST_ITEM_OPTIONS = (
    "choice-band",
    "choice-specs",
    "life-orb",
    "muscle-band",
    "wise-glasses",
)
SUPPORTED_ITEM_OPTIONS = ("unknown", "none", *DAMAGE_TEST_ITEM_OPTIONS)

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
        "source": "user_input",
        "item_id": None,
        "name_en": None,
        "name_ko": None,
        "effects_scope": [],
        "damage_modifier_status": "not_applicable",
        "notes": ["No item has been user-confirmed."],
    }


def user_confirmed_item_profile(item_id: str) -> dict[str, Any]:
    if item_id not in DAMAGE_TEST_ITEM_OPTIONS:
        raise ValueError(f"Unsupported damage-test item option: {item_id}")
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": item_id,
        "name_en": ITEM_LABELS[item_id],
        "name_ko": None,
        "effects_scope": ["damage_modifier"],
        "legality_status": "not_legal_or_unconfirmed",
        "effect_support_status": DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL,
        "damage_modifier_status": "applied",
        "ui_status": "damage_test_only",
        "notes": list(ITEM_NOTES[item_id]),
    }


def item_profile_from_legal_item(item: dict[str, Any]) -> dict[str, Any]:
    item_id = str(item["item_id"])
    effect_support_status = str(item.get("effect_support_status", LEGAL_BUT_NOT_MODELED))
    return {
        "status": "user_confirmed",
        "source": "user_input",
        "item_id": item_id,
        "name_en": item.get("name_en"),
        "name_ko": item.get("name_ko"),
        "effects_scope": [],
        "legality_status": item.get("legality_status", "legal"),
        "effect_support_status": effect_support_status,
        "damage_modifier_status": "not_applied",
        "ui_status": item.get("ui_status", "recognized_not_modeled"),
        "notes": list(item.get("notes") if isinstance(item.get("notes"), list) else []),
    }


def unknown_item_option() -> dict[str, Any]:
    return {
        "option_id": "unknown",
        "label": "Unknown item",
        "profile": unknown_item_profile(),
    }


def no_item_option() -> dict[str, Any]:
    return {
        "option_id": "none",
        "label": "No item",
        "profile": no_item_profile(),
    }


def legal_item_options_from_repository(repository: Any) -> list[dict[str, Any]]:
    options = [unknown_item_option(), no_item_option()]
    for item in repository.list_legal_items():
        options.append(
            {
                "option_id": str(item["item_id"]),
                "label": _legal_item_label(item),
                "profile": item_profile_from_legal_item(item),
            }
        )
    return options


def legacy_damage_test_item_options() -> list[dict[str, Any]]:
    return [
        unknown_item_option(),
        no_item_option(),
        *[
            {
                "option_id": item_id,
                "label": ITEM_LABELS[item_id],
                "profile": user_confirmed_item_profile(item_id),
            }
            for item_id in DAMAGE_TEST_ITEM_OPTIONS
        ],
    ]


def item_profile_from_option(
    option_id: str,
    *,
    role_key: str = "my_active",
    item_options: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    option = _find_item_option(option_id, item_options)
    if option is not None:
        return deepcopy(option["profile"])
    if option_id == "unknown":
        return unknown_item_profile()
    if option_id == "none":
        return no_item_profile()
    if option_id in DAMAGE_TEST_ITEM_OPTIONS:
        return user_confirmed_item_profile(option_id)
    return default_item_profile_for_role(role_key)


def option_from_item_profile(
    profile: dict[str, Any] | None,
    *,
    role_key: str = "my_active",
    item_options: list[dict[str, Any]] | None = None,
) -> str:
    if not isinstance(profile, dict):
        return "unknown" if role_key == "opponent_active" else "none"
    status = profile.get("status")
    if status == "unknown":
        return "unknown"
    if status in {"none", "system_default_none"}:
        return "none"
    item_id = profile.get("item_id")
    if status == "user_confirmed" and isinstance(item_id, str):
        if _find_item_option(item_id, item_options) is not None or item_id in DAMAGE_TEST_ITEM_OPTIONS:
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
        label = str(effective.get("name_en") or effective.get("item_id") or "Item")
        return label[:8]
    return "Item"


class ItemProfileDialog(QDialog):
    def __init__(
        self,
        *,
        pokemon_name: str,
        current_profile: dict[str, Any] | None = None,
        role_key: str = "my_active",
        item_options: list[dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Held Item")
        self._role_key = role_key
        self._item_options = item_options or legacy_damage_test_item_options()
        self._result_profile: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"{pokemon_name} held item")
        title.setStyleSheet("font-weight: 700; color: #17202A;")
        layout.addWidget(title)

        self.item_combo = QComboBox()
        for option in self._item_options:
            self.item_combo.addItem(str(option["label"]), option["option_id"])
        selected = option_from_item_profile(
            current_profile,
            role_key=role_key,
            item_options=self._item_options,
        )
        index = self.item_combo.findData(selected)
        if index >= 0:
            self.item_combo.setCurrentIndex(index)
        layout.addWidget(self.item_combo)

        hint = QLabel(
            "현재 목록은 포켓몬 챔피언스 Regulation M-A legal item fixture를 기반으로 합니다.\n"
            "합법 아이템이어도 효과가 계산되지 않을 수 있으며, 효과는 item_effects가 applied일 때만 반영됩니다.\n"
            "구애 고정, 반동, 스피드, 회복, 생존 효과, KO 확률은 아직 계산하지 않습니다."
        )
        hint.setText(
            "현재 목록은 포켓몬 챔피언스 Regulation M-A legal item fixture를 기반으로 합니다.\n"
            "합법 아이템이어도 효과가 계산되지 않을 수 있으며, 효과는 item_effects가 applied일 때만 반영됩니다.\n"
            "구애 고정, 반동, 스피드, 회복, 생존 효과, KO 확률은 아직 계산하지 않습니다."
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
        self._result_profile = item_profile_from_option(
            option_id,
            role_key=self._role_key,
            item_options=self._item_options,
        )
        self.accept()

    def _reset_and_accept(self) -> None:
        self._result_profile = None
        self.accept()


def _find_item_option(
    option_id: str,
    item_options: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if item_options is None:
        return None
    for option in item_options:
        if option.get("option_id") == option_id:
            return option
    return None


def _legal_item_label(item: dict[str, Any]) -> str:
    name = str(item.get("name_en") or item.get("item_id"))
    effect_support_status = str(item.get("effect_support_status", ""))
    if effect_support_status == LEGAL_AND_DAMAGE_SUPPORTED:
        return f"{name} (legal, damage support recognized)"
    return f"{name} (legal, effect not modeled)"
