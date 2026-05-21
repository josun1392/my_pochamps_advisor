from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CHAMPIONS_LEGAL_ITEMS_PATH = Path("data/static/champions_legal_items.json")

LEGAL_AND_DAMAGE_SUPPORTED = "legal_and_damage_supported"
LEGAL_BUT_NOT_MODELED = "legal_but_not_modeled"
DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL = "damage_supported_but_not_champions_legal"
ILLEGAL_OR_EXCLUDED = "illegal_or_excluded"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class ChampionsItemClassification:
    item_id: str
    legal: bool
    classification: str
    legality_status: str
    effect_support_status: str
    ui_status: str
    name_en: str | None = None
    name_ko: str | None = None
    category: str | None = None
    legality_confidence: str | None = None
    effect_support: dict[str, Any] | None = None
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name_en": self.name_en,
            "name_ko": self.name_ko,
            "category": self.category,
            "legal": self.legal,
            "classification": self.classification,
            "legality_status": self.legality_status,
            "legality_confidence": self.legality_confidence,
            "effect_support_status": self.effect_support_status,
            "ui_status": self.ui_status,
            "effect_support": self.effect_support or {},
            "notes": self.notes or [],
        }


def load_champions_legal_items(path: Path | None = None) -> dict[str, Any]:
    fixture_path = path or DEFAULT_CHAMPIONS_LEGAL_ITEMS_PATH
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    _validate_fixture(data)
    return data


class ChampionsItemRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_CHAMPIONS_LEGAL_ITEMS_PATH
        self.data = load_champions_legal_items(self.path)
        self._legal_items = self._index_items(self.data.get("items", []))
        self._damage_supported_non_legal_items = self._index_items(
            self.data.get("damage_supported_non_legal_items", [])
        )

    @property
    def source_refs(self) -> list[dict[str, Any]]:
        return list(self.data["source_refs"])

    @property
    def regulation(self) -> str:
        return self.data["regulation"]

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        normalized = normalize_item_id(item_id)
        item = self._legal_items.get(normalized) or self._damage_supported_non_legal_items.get(normalized)
        if item is None:
            return None
        return self.classify_item(normalized)

    def is_legal_item(self, item_id: str) -> bool:
        return bool(self.classify_item(item_id)["legal"])

    def get_legality_status(self, item_id: str) -> str:
        return str(self.classify_item(item_id)["legality_status"])

    def get_effect_support_status(self, item_id: str) -> str:
        return str(self.classify_item(item_id)["effect_support_status"])

    def get_ui_status(self, item_id: str) -> str:
        return str(self.classify_item(item_id)["ui_status"])

    def list_legal_items(self) -> list[dict[str, Any]]:
        return [self.classify_item(item_id) for item_id in sorted(self._legal_items)]

    def list_damage_supported_non_legal_items(self) -> list[dict[str, Any]]:
        return [
            self.classify_item(item_id)
            for item_id in sorted(self._damage_supported_non_legal_items)
        ]

    def classify_item(self, item_id: str) -> dict[str, Any]:
        normalized = normalize_item_id(item_id)
        if normalized in self._legal_items:
            return self._classification_for_fixture_item(self._legal_items[normalized]).to_dict()
        if normalized in self._damage_supported_non_legal_items:
            return self._classification_for_fixture_item(
                self._damage_supported_non_legal_items[normalized]
            ).to_dict()
        return ChampionsItemClassification(
            item_id=normalized,
            legal=False,
            classification=UNKNOWN,
            legality_status=UNKNOWN,
            legality_confidence=UNKNOWN,
            effect_support_status=UNKNOWN,
            ui_status=UNKNOWN,
            notes=["Item is not present in the Champions legal item sentinel fixture."],
        ).to_dict()

    @staticmethod
    def _index_items(items: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(items, list):
            return {}
        indexed: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("item_id")
            if isinstance(item_id, str) and item_id:
                indexed[normalize_item_id(item_id)] = item
        return indexed

    @staticmethod
    def _classification_for_fixture_item(item: dict[str, Any]) -> ChampionsItemClassification:
        effect_support_status = _string_value(item, "effect_support_status", UNKNOWN)
        legal = bool(item.get("legal", False))
        classification = _classification_from_item(legal, effect_support_status)
        return ChampionsItemClassification(
            item_id=normalize_item_id(_string_value(item, "item_id", "")),
            name_en=_nullable_string(item.get("name_en")),
            name_ko=_nullable_string(item.get("name_ko")),
            category=_nullable_string(item.get("category")),
            legal=legal,
            classification=classification,
            legality_status=_string_value(item, "legality_status", UNKNOWN),
            legality_confidence=_nullable_string(item.get("legality_confidence")),
            effect_support_status=effect_support_status,
            ui_status=_string_value(item, "ui_status", UNKNOWN),
            effect_support=item.get("effect_support") if isinstance(item.get("effect_support"), dict) else {},
            notes=item.get("notes") if isinstance(item.get("notes"), list) else [],
        )


def normalize_item_id(item_id: str) -> str:
    return item_id.strip().lower().replace("_", "-").replace(" ", "-")


def _classification_from_item(legal: bool, effect_support_status: str) -> str:
    if effect_support_status == LEGAL_AND_DAMAGE_SUPPORTED:
        return LEGAL_AND_DAMAGE_SUPPORTED if legal else DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL
    if effect_support_status == LEGAL_BUT_NOT_MODELED:
        return LEGAL_BUT_NOT_MODELED if legal else ILLEGAL_OR_EXCLUDED
    if effect_support_status == DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL:
        return DAMAGE_SUPPORTED_BUT_NOT_CHAMPIONS_LEGAL
    if not legal:
        return ILLEGAL_OR_EXCLUDED
    return effect_support_status


def _validate_fixture(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Champions legal item fixture must be a JSON object.")
    required_top_level = {
        "format",
        "regulation",
        "source_kind",
        "fetched_at",
        "source_refs",
        "items",
        "damage_supported_non_legal_items",
    }
    missing = sorted(required_top_level - set(data))
    if missing:
        raise ValueError(f"Champions legal item fixture missing fields: {missing}")
    if data["format"] != "pokemon_champions":
        raise ValueError("Champions legal item fixture format must be pokemon_champions.")
    if not isinstance(data["source_refs"], list) or not data["source_refs"]:
        raise ValueError("Champions legal item fixture must include source_refs.")
    _validate_item_list(data["items"], "items")
    _validate_item_list(data["damage_supported_non_legal_items"], "damage_supported_non_legal_items")


def _validate_item_list(items: Any, field_name: str) -> None:
    if not isinstance(items, list):
        raise ValueError(f"Champions legal item fixture field {field_name} must be a list.")
    required = {"item_id", "legal", "legality_status", "effect_support_status", "ui_status"}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"Champions legal item fixture field {field_name} contains a non-object item.")
        missing = sorted(required - set(item))
        if missing:
            item_id = item.get("item_id", "<missing item_id>")
            raise ValueError(f"Champions legal item {item_id} missing fields: {missing}")


def _string_value(item: dict[str, Any], key: str, default: str) -> str:
    value = item.get(key)
    return value if isinstance(value, str) and value else default


def _nullable_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
