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


def test_repository_reads_champions_cache_format(tmp_path: Path) -> None:
    repo = _repo_with_champions_cache(tmp_path)

    view = repo.get("abomasnow")

    assert view.en == "abomasnow"
    assert view.ko == "눈설왕"
    assert view.types_en == ["grass", "ice"]
    assert view.types_ko == ["풀", "얼음"]
    assert view.base_stats == {
        "hp": 90,
        "attack": 92,
        "defense": 75,
        "special-attack": 92,
        "special-defense": 85,
        "speed": 60,
    }
    assert view.abilities_en == ["snow-warning", "soundproof"]
    assert view.abilities_ko == ["눈퍼뜨리기", "방음"]
    assert view.moves_en == ["blizzard", "ice-punch", "earthquake"]


def test_repository_uses_entity_id_for_champions_forms(tmp_path: Path) -> None:
    repo = _repo_with_champions_cache(tmp_path)
    _write_champions_pokemon(
        tmp_path / "cache" / "pokemon",
        "abomasnow-mega",
        {"en": "Mega Abomasnow", "ko": "메가눈설왕"},
    )

    view = repo.get("abomasnow-mega")

    assert view.en == "abomasnow-mega"
    assert view.ko == "메가눈설왕"


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


def _repo_with_champions_cache(tmp_path: Path) -> PokemonRepository:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    champions_dir = tmp_path / "cache" / "pokemon"
    champions_dir.mkdir(parents=True)
    data = {
        "entity_id": "abomasnow",
        "name": {"en": "abomasnow", "ko": "눈설왕"},
        "types": ["grass", "ice"],
        "types_ko": ["풀", "얼음"],
        "abilities": [
            {"name": "snow-warning", "name_ko": "눈퍼뜨리기"},
            {"name": "soundproof", "name_ko": "방음"},
        ],
        "base_stats": {
            "hp": 90,
            "atk": 92,
            "def": 75,
            "spa": 92,
            "spd": 85,
            "spe": 60,
        },
        "movepool": {
            "level_up": ["blizzard", "ice-punch"],
            "machine": ["ice-punch", "earthquake"],
            "egg": [],
            "tutor": [],
        },
    }
    with (champions_dir / "abomasnow.json").open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)
    mapping_path = tmp_path / "ko_mapping.json"
    mapping = {
        "_built_at": "2026-04-27T12:00:00Z",
        "_version": 1,
        "pokemon": {},
        "moves": {},
        "abilities": {},
        "types": {"grass": "풀", "ice": "얼음"},
        "_unmapped": {"pokemon": [], "moves": [], "abilities": [], "types": []},
        "_overridden": {"pokemon": [], "moves": [], "abilities": [], "types": []},
    }
    with mapping_path.open("w", encoding="utf-8") as file:
        json.dump(mapping, file, ensure_ascii=False)
    return PokemonRepository(cache, KoMappingLoader(mapping_path), champions_cache_dir=champions_dir)


def _write_champions_pokemon(champions_dir: Path, entity_id: str, name: dict[str, str]) -> None:
    data = {
        "entity_id": entity_id,
        "name": name,
        "types": ["grass", "ice"],
        "types_ko": ["풀", "얼음"],
        "abilities": [],
        "base_stats": {
            "hp": 90,
            "atk": 92,
            "def": 75,
            "spa": 92,
            "spd": 85,
            "spe": 60,
        },
        "movepool": {"level_up": [], "machine": [], "egg": [], "tutor": []},
    }
    with (champions_dir / f"{entity_id}.json").open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)
