from __future__ import annotations

from dataclasses import dataclass
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


class PokemonRepository:
    def __init__(self, cache_manager: CacheManager, ko_loader: KoMappingLoader) -> None:
        self.cache_manager = cache_manager
        self.ko_loader = ko_loader

    def get(self, en_id: str) -> PokemonView:
        """캐시 + 매핑 조회. 캐시 미스 시 RuntimeError."""
        data = self.cache_manager.get("pokemon", en_id)
        if data is None:
            raise RuntimeError(f"캐시된 포켓몬을 찾을 수 없습니다: {en_id}")

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
        )


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise RuntimeError(f"필수 문자열 필드가 없습니다: {key}")
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
