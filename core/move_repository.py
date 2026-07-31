from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
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
    drain: int | None = None
    min_hits: int | None = None
    max_hits: int | None = None
    healing: int | None = None
    target: str | None = None
    effect_category: str | None = None
    ailment: str | None = None
    stat_changes: tuple[tuple[str, int], ...] = ()


class MoveRepository:
    def __init__(
        self,
        cache_manager: CacheManager,
        ko_loader: KoMappingLoader,
        champions_move_pool: ChampionsMovePoolRepository | None = None,
    ) -> None:
        self.cache_manager = cache_manager
        self.ko_loader = ko_loader
        self.champions_move_pool = champions_move_pool or ChampionsMovePoolRepository()

    def get(self, move_id: str) -> MoveView:
        data = self.cache_manager.get("moves", move_id)
        if data is None:
            return self._get_from_champions_movepool(move_id)

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
            drain=_optional_int(data.get("meta", {}).get("drain") if isinstance(data.get("meta"), dict) else None),
            min_hits=_optional_int(data.get("meta", {}).get("min_hits") if isinstance(data.get("meta"), dict) else None),
            max_hits=_optional_int(data.get("meta", {}).get("max_hits") if isinstance(data.get("meta"), dict) else None),
            healing=_optional_int(data.get("meta", {}).get("healing") if isinstance(data.get("meta"), dict) else None),
            target=_optional_str(data.get("target")),
            effect_category=_optional_str(data.get("meta", {}).get("category") if isinstance(data.get("meta"), dict) else None),
            ailment=_optional_str(data.get("meta", {}).get("ailment") if isinstance(data.get("meta"), dict) else None),
            stat_changes=_stat_changes(data.get("stat_changes")),
        )

    def _get_from_champions_movepool(self, move_id: str) -> MoveView:
        data = self.champions_move_pool.get_move_metadata(move_id)
        if data is None:
            raise RuntimeError(f"Move is missing from cache: {move_id}")
        name_en = _required_str(data, "name_en")
        move_type = _required_str(data, "type")
        category = _required_str(data, "category")
        return MoveView(
            move_id=move_id,
            name_en=name_en,
            name_ko=self.ko_loader.get_move_ko(move_id),
            type=move_type,
            category=category,
            power=_optional_int(data.get("power")),
            accuracy=_optional_int(data.get("accuracy")),
            pp=_optional_int(data.get("pp")),
            drain=_optional_int(data.get("drain")),
            min_hits=_optional_int(data.get("min_hits")), max_hits=_optional_int(data.get("max_hits")),
            healing=_optional_int(data.get("healing")),
            target=_optional_str(data.get("target")),
            effect_category=_optional_str(data.get("effect_category")),
            ailment=_optional_str(data.get("ailment")),
            stat_changes=_stat_changes(data.get("stat_changes")),
        )


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Move cache is missing required string field: {key}")
    return value


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _stat_changes(value: Any) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, list):
        return ()
    changes: list[tuple[str, int]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        stat, change = item.get("stat"), item.get("change")
        if isinstance(stat, str) and stat and isinstance(change, int) and not isinstance(change, bool) and change:
            changes.append((stat, change))
    return tuple(changes)


def _localized_name(data: dict[str, Any], lang: str) -> str | None:
    names = data.get("names")
    if not isinstance(names, dict):
        return None
    value = names.get(lang)
    return value if isinstance(value, str) and value else None
