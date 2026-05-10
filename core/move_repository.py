from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.cache_manager import CacheManager
from core.ko_mapping_loader import KoMappingLoader


@dataclass(frozen=True)
class MoveView:
    move_id: str
    name_en: str
    name_ko: str | None
    type: str
    category: str
    power: int | None
    accuracy: int | None
    pp: int | None


class MoveRepository:
    def __init__(self, cache_manager: CacheManager, ko_loader: KoMappingLoader) -> None:
        self.cache_manager = cache_manager
        self.ko_loader = ko_loader

    def get(self, move_id: str) -> MoveView:
        data = self.cache_manager.get("moves", move_id)
        if data is None:
            raise RuntimeError(f"Move is missing from cache: {move_id}")

        name = _required_str(data, "name")
        move_type = _required_str(data, "type")
        category = _required_str(data, "damage_class")
        return MoveView(
            move_id=name,
            name_en=_localized_name(data, "en") or name,
            name_ko=self.ko_loader.get_move_ko(name) or _localized_name(data, "ko"),
            type=move_type,
            category=category,
            power=_optional_int(data.get("power")),
            accuracy=_optional_int(data.get("accuracy")),
            pp=_optional_int(data.get("pp")),
        )


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Move cache is missing required string field: {key}")
    return value


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _localized_name(data: dict[str, Any], lang: str) -> str | None:
    names = data.get("names")
    if not isinstance(names, dict):
        return None
    value = names.get(lang)
    return value if isinstance(value, str) and value else None
