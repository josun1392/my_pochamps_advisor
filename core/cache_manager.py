from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CacheData = dict[str, Any]


class CacheManager:
    """디스크 캐시의 단일 진입점."""

    CATEGORIES = ("pokemon", "moves", "abilities", "types", "species")

    def __init__(self, cache_root: Path = Path("data/cache/pokeapi")) -> None:
        self.cache_root = cache_root
        self.index_path = cache_root.parent.parent / "meta" / "cache_index.json"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        for category in self.CATEGORIES:
            self._category_dir(category).mkdir(parents=True, exist_ok=True)
        self._index = self._load_index()

    def get(self, category: str, identifier: int | str) -> CacheData | None:
        """캐시 hit이면 dict 반환, miss면 None."""
        normalized_id = self._resolve_identifier(category, identifier)
        if normalized_id is None:
            return None

        path = self._cache_path(category, normalized_id)
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None
        return data

    def put(self, category: str, identifier: int, data: CacheData) -> None:
        """JSON으로 저장. tempfile에 쓴 뒤 rename하는 atomic write."""
        self._validate_category(category)
        path = self._cache_path(category, identifier)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=path.parent,
                encoding="utf-8",
                suffix=".tmp",
            ) as temp_file:
                json.dump(data, temp_file, ensure_ascii=False, indent=2, sort_keys=True)
                temp_file.write("\n")
                temp_path = Path(temp_file.name)

            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

        self._update_index(category, identifier, data)

    def has(self, category: str, identifier: int) -> bool:
        self._validate_category(category)
        return self._cache_path(category, identifier).exists()

    def stats(self) -> dict[str, int]:
        """카테고리별 캐시 개수 반환. 디버깅용."""
        return {
            category: len(list(self._category_dir(category).glob("*.json")))
            for category in self.CATEGORIES
        }

    def resolve_name(self, category: str, name: str) -> int | None:
        self._validate_category(category)
        return self._index["name_to_id"].get(category, {}).get(name.lower())

    def _resolve_identifier(self, category: str, identifier: int | str) -> int | None:
        self._validate_category(category)
        if isinstance(identifier, int):
            return identifier
        if identifier.isdigit():
            return int(identifier)
        return self.resolve_name(category, identifier)

    def _update_index(self, category: str, identifier: int, data: CacheData) -> None:
        name = data.get("name")
        if isinstance(name, str) and name:
            self._index["name_to_id"].setdefault(category, {})[name.lower()] = identifier
        self._index["updated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
        self._write_index()

    def _load_index(self) -> CacheData:
        if self.index_path.exists():
            try:
                with self.index_path.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, dict):
                    return self._with_index_defaults(data)
            except (OSError, json.JSONDecodeError):
                pass
        return self._with_index_defaults({})

    def _write_index(self) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=self.index_path.parent,
                encoding="utf-8",
                suffix=".tmp",
            ) as temp_file:
                json.dump(self._index, temp_file, ensure_ascii=False, indent=2, sort_keys=True)
                temp_file.write("\n")
                temp_path = Path(temp_file.name)
            os.replace(temp_path, self.index_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def _with_index_defaults(self, data: CacheData) -> CacheData:
        data.setdefault("version", 1)
        data.setdefault("source", "pokeapi")
        data.setdefault("created_at", datetime.now(UTC).replace(microsecond=0).isoformat())
        data.setdefault("updated_at", None)
        name_to_id = data.setdefault("name_to_id", {})
        for category in self.CATEGORIES:
            name_to_id.setdefault(category, {})
        return data

    def _cache_path(self, category: str, identifier: int) -> Path:
        self._validate_category(category)
        return self._category_dir(category) / f"{identifier}.json"

    def _category_dir(self, category: str) -> Path:
        self._validate_category(category)
        return self.cache_root / category

    def _validate_category(self, category: str) -> None:
        if category not in self.CATEGORIES:
            raise ValueError(f"지원하지 않는 캐시 카테고리: {category}")
