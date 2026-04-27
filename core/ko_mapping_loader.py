from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KoMappingLoader:
    """ko_mapping.json을 메모리에 로드하고 빠른 조회 제공."""

    def __init__(self, mapping_path: Path = Path("data/ko_mapping.json")) -> None:
        self.mapping_path = mapping_path
        with mapping_path.open("r", encoding="utf-8") as file:
            mapping = json.load(file)
        if not isinstance(mapping, dict):
            raise ValueError(f"한국어 매핑 파일 형식이 올바르지 않습니다: {mapping_path}")
        self._mapping: dict[str, Any] = mapping
        self._reverse_cache: dict[str, dict[str, str]] | None = None

    def get_pokemon_ko(self, en_name: str) -> str | None:
        return self._get_ko("pokemon", en_name)

    def get_move_ko(self, en_name: str) -> str | None:
        return self._get_ko("moves", en_name)

    def get_ability_ko(self, en_name: str) -> str | None:
        return self._get_ko("abilities", en_name)

    def get_type_ko(self, en_name: str) -> str | None:
        return self._get_ko("types", en_name)

    def get_pokemon_en(self, ko_name: str) -> str | None:
        return self._reverse_index["pokemon"].get(ko_name)

    def stats(self) -> dict[str, int]:
        return {
            category: len(self._mapping.get(category, {}))
            for category in ("pokemon", "moves", "abilities", "types")
        }

    @property
    def _reverse_index(self) -> dict[str, dict[str, str]]:
        if self._reverse_cache is None:
            self._reverse_cache = {
                category: {ko: en for en, ko in self._mapping.get(category, {}).items()}
                for category in ("pokemon", "moves", "abilities", "types")
            }
        return self._reverse_cache

    def _get_ko(self, category: str, en_name: str) -> str | None:
        value = self._mapping.get(category, {}).get(en_name)
        return value if isinstance(value, str) else None
