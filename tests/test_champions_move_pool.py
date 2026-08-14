from __future__ import annotations

import json
from pathlib import Path

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository
from core.pokeapi_fetcher import PokeAPIFetcher
from ui.main_window import _move_payload


def test_charizard_sample_excludes_historical_and_globally_denied_moves() -> None:
    repo = ChampionsMovePoolRepository()

    allowed_moves = repo.get_allowed_move_ids_for_pokemon("charizard")

    assert "flamethrower" in allowed_moves
    assert "hidden-power" not in allowed_moves
    assert "tera-blast" not in allowed_moves


def test_empty_local_movepool_sentinels_have_sample_fixtures() -> None:
    repo = ChampionsMovePoolRepository()

    assert repo.get_allowed_move_ids_for_pokemon("vanilluxe")
    assert repo.get_allowed_move_ids_for_pokemon("starmie")


def test_unknown_pokemon_returns_unavailable_status() -> None:
    repo = ChampionsMovePoolRepository()

    assert repo.get_allowed_move_ids_for_pokemon("missingno") == set()
    assert repo.status_for_pokemon("missingno") == {
        "status": "unavailable_missing_champions_movepool",
        "pokemon_id": "missingno",
        "reason": "No Serebii-derived Champions move pool fixture/cache exists for this Pokemon.",
    }


def test_filter_champions_moves_intersects_candidates() -> None:
    repo = ChampionsMovePoolRepository()

    filtered = repo.filter_champions_moves_for_pokemon(
        "charizard",
        {"flamethrower", "hidden-power", "surf"},
    )

    assert filtered == {"flamethrower"}


def test_pokeapi_move_metadata_still_loads_for_legal_sample_move() -> None:
    move = MoveRepository(CacheManager(), KoMappingLoader()).get("flamethrower")

    assert move.move_id == "flamethrower"
    assert move.type == "fire"
    assert move.category == "special"
    assert move.power == 90


def test_cached_pokeapi_priority_is_explicit_and_survives_move_repository_reload(tmp_path: Path) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    cache.put("moves", 85, PokeAPIFetcher._normalize_move(_raw_move("thunderbolt", 85, 0)))
    cache.put("moves", 98, PokeAPIFetcher._normalize_move(_raw_move("quick-attack", 98, 1)))
    repository = MoveRepository(cache, KoMappingLoader())

    assert repository.get("thunderbolt").priority == 0
    assert repository.get("quick-attack").priority == 1

    assert _move_payload(repository.get("thunderbolt"), 0)["priority"] == 0


def test_missing_or_malformed_cached_priority_stays_unknown(tmp_path: Path) -> None:
    cache = CacheManager(tmp_path / "cache" / "pokeapi")
    missing = PokeAPIFetcher._normalize_move(_raw_move("missing-priority", 1, None))
    malformed = PokeAPIFetcher._normalize_move(_raw_move("malformed-priority", 2, "0"))
    cache.put("moves", 1, missing)
    cache.put("moves", 2, malformed)
    repository = MoveRepository(cache, KoMappingLoader())

    assert repository.get("missing-priority").priority is None
    assert repository.get("malformed-priority").priority is None


def test_champions_fallback_forwards_only_explicit_priority(tmp_path: Path) -> None:
    cache_dir = tmp_path / "champions"
    cache_dir.mkdir()
    (cache_dir / "fixture.json").write_text(json.dumps({"moves": [
        {"move_id": "quick-attack", "name_en": "Quick Attack", "type": "normal", "category": "physical", "power": 40, "accuracy": 100, "pp": 30, "priority": 1},
        {"move_id": "unknown-priority", "name_en": "Unknown Priority", "type": "normal", "category": "physical", "power": 40, "accuracy": 100, "pp": 30},
    ]}), encoding="utf-8")
    repository = MoveRepository(
        CacheManager(tmp_path / "cache" / "pokeapi"), KoMappingLoader(),
        ChampionsMovePoolRepository(cache_dir=cache_dir),
    )

    assert repository.get("quick-attack").priority == 1
    assert repository.get("unknown-priority").priority is None


def test_fixture_path_can_be_overridden(tmp_path: Path) -> None:
    repo = ChampionsMovePoolRepository(cache_dir=tmp_path)

    assert repo.get_allowed_move_ids_for_pokemon("charizard") == set()


def _raw_move(name: str, identifier: int, priority: int | str | None) -> dict:
    return {
        "id": identifier,
        "name": name,
        "names": [],
        "type": {"name": "electric"},
        "damage_class": {"name": "special"},
        "power": 90,
        "accuracy": 100,
        "pp": 15,
        "priority": priority,
        "target": {"name": "selected-pokemon"},
        "meta": {},
        "stat_changes": [],
    }
