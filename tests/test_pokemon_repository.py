from __future__ import annotations

from pathlib import Path
import json

import pytest

from core.cache_manager import CacheManager
from core.ko_mapping_loader import KoMappingLoader
from core.pokemon_repository import PokemonRepository


def test_repository_returns_korean_names(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    view = repo.get("garchomp")

    assert view.ko == "한카리아스"


def test_repository_returns_typed_stats(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    view = repo.get("garchomp")

    assert set(view.base_stats) == {
        "hp",
        "attack",
        "defense",
        "special-attack",
        "special-defense",
        "speed",
    }
    assert all(isinstance(value, int) for value in view.base_stats.values())


def test_repository_raises_on_cache_miss(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(RuntimeError, match="캐시된 포켓몬"):
        repo.get("missingno")


def test_repository_resolves_type_korean_names(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    view = repo.get("garchomp")

    assert view.types_ko == ["드래곤", "땅"]


def _repo(tmp_path: Path) -> PokemonRepository:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    cache.put(
        "pokemon",
        445,
        {
            "id": 445,
            "name": "garchomp",
            "types": ["dragon", "ground"],
            "abilities": [
                {"name": "sand-veil", "is_hidden": False},
                {"name": "rough-skin", "is_hidden": True},
            ],
            "stats": {
                "hp": 108,
                "attack": 130,
                "defense": 95,
                "special-attack": 80,
                "special-defense": 85,
                "speed": 102,
            },
        },
    )
    mapping_path = tmp_path / "ko_mapping.json"
    mapping = {
        "_built_at": "2026-04-27T12:00:00Z",
        "_version": 1,
        "pokemon": {"garchomp": "한카리아스"},
        "moves": {},
        "abilities": {"sand-veil": "모래숨기", "rough-skin": "까칠한피부"},
        "types": {"dragon": "드래곤", "ground": "땅"},
        "_unmapped": {"pokemon": [], "moves": [], "abilities": [], "types": []},
        "_overridden": {"pokemon": [], "moves": [], "abilities": [], "types": []},
    }
    with mapping_path.open("w", encoding="utf-8") as file:
        json.dump(mapping, file, ensure_ascii=False)
    return PokemonRepository(cache, KoMappingLoader(mapping_path))
