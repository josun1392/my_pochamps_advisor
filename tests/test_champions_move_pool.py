from __future__ import annotations

from pathlib import Path

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository


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


def test_fixture_path_can_be_overridden(tmp_path: Path) -> None:
    repo = ChampionsMovePoolRepository(cache_dir=tmp_path)

    assert repo.get_allowed_move_ids_for_pokemon("charizard") == set()
