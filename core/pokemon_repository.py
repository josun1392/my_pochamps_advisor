from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.cache_manager import CacheManager
from core.ko_mapping_loader import KoMappingLoader


STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


@dataclass(frozen=True)
class PokemonView:
    en: str
    ko: str
    types_en: list[str]
    types_ko: list[str]
    base_stats: dict[str, int]
    abilities_en: list[str]
    abilities_ko: list[str]
    moves_en: list[str]


class PokemonRepository:
    def __init__(
        self,
        cache_manager: CacheManager,
        ko_loader: KoMappingLoader,
        champions_cache_dir: Path = Path("data/cache/pokemon"),
    ) -> None:
        self.cache_manager = cache_manager
        self.ko_loader = ko_loader
        self.champions_cache_dir = champions_cache_dir

    def get(self, en_id: str) -> PokemonView:
        """캐시 + 매핑 조회. 캐시 미스 시 RuntimeError."""
        data = self.cache_manager.get("pokemon", en_id)
        if data is not None:
            return self._view_from_pokeapi_cache(data, en_id)

        champions_data = self._load_champions_cache(en_id)
        if champions_data is None:
            raise RuntimeError(f"캐시된 포켓몬을 찾을 수 없습니다: {en_id}")
        return self._view_from_champions_cache(champions_data, en_id)

    def _view_from_pokeapi_cache(self, data: dict[str, Any], en_id: str) -> PokemonView:
        name = _required_str(data, "name")
        types_en = _string_list(data.get("types"))
        abilities_en = [
            ability["name"]
            for ability in data.get("abilities", [])
            if isinstance(ability, dict) and isinstance(ability.get("name"), str)
        ]
        stats = data.get("stats")
        if not isinstance(stats, dict):
            raise RuntimeError(f"포켓몬 종족값 캐시가 올바르지 않습니다: {en_id}")

        base_stats = {key: int(stats[key]) for key in STAT_KEYS if key in stats}
        missing_stats = [key for key in STAT_KEYS if key not in base_stats]
        if missing_stats:
            raise RuntimeError(f"포켓몬 종족값이 누락되었습니다: {en_id} / {missing_stats}")

        return PokemonView(
            en=name,
            ko=self.ko_loader.get_pokemon_ko(name) or name,
            types_en=types_en,
            types_ko=[self.ko_loader.get_type_ko(type_name) or type_name for type_name in types_en],
            base_stats=base_stats,
            abilities_en=abilities_en,
            abilities_ko=[
                self.ko_loader.get_ability_ko(ability_name) or ability_name
                for ability_name in abilities_en
            ],
            moves_en=_string_list(data.get("moves")),
        )

    def _view_from_champions_cache(self, data: dict[str, Any], en_id: str) -> PokemonView:
        name_data = data.get("name")
        entity_id = _optional_str(data.get("entity_id")) or en_id
        if isinstance(name_data, dict):
            name = entity_id
            name_ko = _optional_str(name_data.get("ko"))
        else:
            name = entity_id
            name_ko = None

        types_en = _string_list(data.get("types"))
        types_ko = _string_list(data.get("types_ko"))
        if not types_ko:
            types_ko = [self.ko_loader.get_type_ko(type_name) or type_name for type_name in types_en]

        abilities_en = []
        abilities_ko = []
        for ability in data.get("abilities", []):
            if not isinstance(ability, dict):
                continue
            ability_name = _optional_str(ability.get("name"))
            if ability_name is None:
                continue
            abilities_en.append(ability_name)
            abilities_ko.append(
                _optional_str(ability.get("name_ko"))
                or self.ko_loader.get_ability_ko(ability_name)
                or ability_name
            )

        base_stats = _champions_base_stats(data.get("base_stats"))
        missing_stats = [key for key in STAT_KEYS if key not in base_stats]
        if missing_stats:
            raise RuntimeError(f"포켓몬 종족값이 누락되었습니다: {en_id} / {missing_stats}")

        return PokemonView(
            en=name,
            ko=name_ko or self.ko_loader.get_pokemon_ko(name) or name,
            types_en=types_en,
            types_ko=types_ko,
            base_stats=base_stats,
            abilities_en=abilities_en,
            abilities_ko=abilities_ko,
            moves_en=_movepool_list(data.get("movepool")),
        )

    def _load_champions_cache(self, en_id: str) -> dict[str, Any] | None:
        path = self.champions_cache_dir / f"{en_id}.json"
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise RuntimeError(f"필수 문자열 필드가 없습니다: {key}")
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _champions_base_stats(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    key_map = {
        "hp": "hp",
        "atk": "attack",
        "def": "defense",
        "spa": "special-attack",
        "spd": "special-defense",
        "spe": "speed",
    }
    stats: dict[str, int] = {}
    for source_key, target_key in key_map.items():
        raw = value.get(source_key)
        if isinstance(raw, int):
            stats[target_key] = raw
    return stats


def _movepool_list(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    moves: list[str] = []
    seen: set[str] = set()
    for source in ("level_up", "machine", "egg", "tutor"):
        for move_id in _string_list(value.get(source)):
            if move_id not in seen:
                moves.append(move_id)
                seen.add(move_id)
    return moves
