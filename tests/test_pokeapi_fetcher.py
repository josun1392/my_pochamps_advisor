from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from core.cache_manager import CacheManager
from core.pokeapi_fetcher import PokeAPIFetcher


def test_cache_miss_in_offline_mode_raises(tmp_path: Path) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    fetcher = PokeAPIFetcher(cache, offline=True)

    with pytest.raises(RuntimeError, match="Offline mode"):
        fetcher.get_pokemon("charizard")


def test_cache_hit_in_offline_mode_returns_data(tmp_path: Path) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    cached = {"id": 6, "name": "charizard", "types": ["fire", "flying"]}
    cache.put("pokemon", 6, cached)
    fetcher = PokeAPIFetcher(cache, offline=True)

    assert fetcher.get_pokemon("charizard") == cached


def test_normalized_pokemon_schema() -> None:
    normalized = PokeAPIFetcher._normalize_pokemon(_pokemon_raw())

    assert set(normalized) == {
        "id",
        "name",
        "types",
        "abilities",
        "stats",
        "sprites",
        "moves",
        "species_url",
        "_fetched_at",
    }
    assert normalized["id"] == 6
    assert normalized["types"] == ["fire", "flying"]
    assert normalized["abilities"] == [
        {"name": "blaze", "is_hidden": False},
        {"name": "solar-power", "is_hidden": True},
    ]
    assert normalized["stats"]["special-attack"] == 109
    assert normalized["moves"] == ["flamethrower", "air-slash"]


def test_atomic_write_prevents_corruption(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    original = {"id": 6, "name": "charizard"}
    cache.put("pokemon", 6, original)

    real_replace = os.replace

    def failing_replace(src: str | bytes | os.PathLike[str], dst: str | bytes | os.PathLike[str]) -> None:
        if Path(dst).name == "6.json":
            raise OSError("simulated replace failure")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        cache.put("pokemon", 6, {"id": 6, "name": "corrupted"})

    path = tmp_path / "cache" / "pokeapi" / "pokemon" / "6.json"
    with path.open("r", encoding="utf-8") as file:
        assert json.load(file) == original


def test_name_to_id_resolution(tmp_path: Path) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    cache.put("pokemon", 6, {"id": 6, "name": "charizard"})

    assert cache.get("pokemon", "charizard") == {"id": 6, "name": "charizard"}


def test_fetcher_uses_session_mock_without_network(tmp_path: Path, mocker: Any) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    fetcher = PokeAPIFetcher(cache)
    response = mocker.Mock()
    response.status_code = 200
    response.json.return_value = _pokemon_raw()
    fetcher.session.get = mocker.Mock(return_value=response)

    result = fetcher.get_pokemon("charizard")

    assert result["id"] == 6
    assert cache.get("pokemon", "charizard")["name"] == "charizard"
    fetcher.session.get.assert_called_once()


def _pokemon_raw() -> dict[str, Any]:
    return {
        "id": 6,
        "name": "charizard",
        "types": [
            {"slot": 1, "type": {"name": "fire"}},
            {"slot": 2, "type": {"name": "flying"}},
        ],
        "abilities": [
            {"ability": {"name": "blaze"}, "is_hidden": False},
            {"ability": {"name": "solar-power"}, "is_hidden": True},
        ],
        "stats": [
            {"base_stat": 78, "stat": {"name": "hp"}},
            {"base_stat": 84, "stat": {"name": "attack"}},
            {"base_stat": 78, "stat": {"name": "defense"}},
            {"base_stat": 109, "stat": {"name": "special-attack"}},
            {"base_stat": 85, "stat": {"name": "special-defense"}},
            {"base_stat": 100, "stat": {"name": "speed"}},
        ],
        "sprites": {
            "front_default": "https://example.test/front.png",
            "front_shiny": "https://example.test/shiny.png",
        },
        "moves": [
            {"move": {"name": "flamethrower"}},
            {"move": {"name": "air-slash"}},
        ],
        "species": {"url": "https://pokeapi.co/api/v2/pokemon-species/6/"},
    }
