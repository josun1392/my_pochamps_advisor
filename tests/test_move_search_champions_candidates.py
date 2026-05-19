from __future__ import annotations

from types import SimpleNamespace

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveRepository
from core.search_engine import SearchEngine
from ui.main_window import _move_search_candidates_for_view


def _view(pokemon_id: str):
    return SimpleNamespace(en=pokemon_id, ko=pokemon_id)


def test_charizard_move_candidates_use_champions_fixture() -> None:
    repo = ChampionsMovePoolRepository()

    candidates, empty_message = _move_search_candidates_for_view(_view("charizard"), repo)

    assert empty_message is None
    assert candidates == repo.get_allowed_move_ids_for_pokemon("charizard")
    assert "flamethrower" in candidates


def test_charizard_move_candidates_do_not_include_historical_or_denied_moves() -> None:
    candidates, _ = _move_search_candidates_for_view(_view("charizard"), ChampionsMovePoolRepository())

    assert "hidden-power" not in candidates
    assert "tera-blast" not in candidates


def test_froslass_move_candidates_do_not_include_tera_blast() -> None:
    candidates, empty_message = _move_search_candidates_for_view(_view("froslass"), ChampionsMovePoolRepository())

    assert empty_message is None
    assert candidates
    assert "tera-blast" not in candidates


def test_empty_local_movepool_sentinels_have_candidates() -> None:
    repo = ChampionsMovePoolRepository()

    vanilluxe_candidates, vanilluxe_message = _move_search_candidates_for_view(_view("vanilluxe"), repo)
    starmie_candidates, starmie_message = _move_search_candidates_for_view(_view("starmie"), repo)

    assert vanilluxe_message is None
    assert starmie_message is None
    assert vanilluxe_candidates
    assert starmie_candidates


def test_unknown_pokemon_does_not_fallback_to_pokeapi_learnset() -> None:
    candidates, empty_message = _move_search_candidates_for_view(_view("garchomp"), ChampionsMovePoolRepository())

    assert candidates == set()
    assert empty_message == "Champions moves unavailable"


def test_pokeapi_move_metadata_still_loads_for_fixture_candidate() -> None:
    move = MoveRepository(CacheManager(), KoMappingLoader()).get("flamethrower")

    assert move.move_id == "flamethrower"
    assert move.type == "fire"
    assert move.category == "special"


def test_sample_fixture_moves_are_added_to_search_index() -> None:
    loader = KoMappingLoader()
    search_engine = SearchEngine(loader)
    repo = ChampionsMovePoolRepository()
    for move_id, name_en in repo.iter_move_search_entries():
        search_engine.add_entry("move", move_id, name_en)

    candidates, _ = _move_search_candidates_for_view(_view("vanilluxe"), repo)
    results = [
        result
        for result in search_engine.search("freeze dry", kind="move", limit=24)
        if result.en in candidates
    ]

    assert [result.en for result in results] == ["freeze-dry"]
