from __future__ import annotations

import json
from pathlib import Path

from core.ko_mapping_loader import KoMappingLoader
from core.search_engine import SearchEngine


def test_korean_prefix_match(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    results = engine.search("리자")

    assert results[0].en == "charizard"
    assert results[0].ko == "리자몽"
    assert results[0].match_type == "prefix"


def test_english_prefix_match(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    results = engine.search("char")

    assert results[0].en == "charizard"
    assert results[0].ko == "리자몽"
    assert results[0].match_type == "prefix"


def test_case_insensitive(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    lower = engine.search("char")
    upper = engine.search("CHAR")
    mixed = engine.search("Char")

    assert [result.en for result in lower] == [result.en for result in upper] == [result.en for result in mixed]


def test_hyphen_space_normalization(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    spaced = engine.search("tera blast", kind="move")
    hyphenated = engine.search("tera-blast", kind="move")
    compact = engine.search("terablast", kind="move")

    assert spaced[0].en == "tera-blast"
    assert hyphenated[0].en == "tera-blast"
    assert compact[0].en == "tera-blast"


def test_fuzzy_typo_tolerance(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    results = engine.search("리잠몽", kind="pokemon")

    assert results[0].en == "charizard"
    assert results[0].match_type == "fuzzy"


def test_kind_filter(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    results = engine.search("리", kind="pokemon")

    assert results
    assert {result.kind for result in results} == {"pokemon"}


def test_empty_query_returns_empty(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    assert engine.search("") == []
    assert engine.search("   ") == []


def test_limit_parameter(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    results = engine.search("리", limit=3)

    assert len(results) == 3


def test_min_score_threshold(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    assert engine.search("zzzz", min_score=0.9) == []


def test_deterministic_ordering(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    first = engine.search("리", limit=10)
    second = engine.search("리", limit=10)

    assert first == second


def test_prefix_beats_fuzzy(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    results = engine.search("리자", limit=10)

    assert results[0].match_type == "prefix"
    assert all(result.match_type != "fuzzy" or results.index(result) > 0 for result in results)


def test_add_pokemon_entries_extends_mapping_index(tmp_path: Path) -> None:
    engine = _engine(tmp_path)

    engine.add_pokemon_entries({"abomasnow": "눈설왕", "alakazam-mega": None})

    korean = engine.search("눈설", kind="pokemon")
    english = engine.search("alakazam", kind="pokemon")

    assert korean[0].en == "abomasnow"
    assert korean[0].ko == "눈설왕"
    assert english[0].en == "alakazam-mega"
    assert english[0].ko == "alakazam-mega"


def _engine(tmp_path: Path) -> SearchEngine:
    return SearchEngine(KoMappingLoader(_write_mapping(tmp_path)))


def _write_mapping(tmp_path: Path) -> Path:
    mapping_path = tmp_path / "ko_mapping.json"
    mapping = {
        "_built_at": "2026-04-27T11:00:00Z",
        "_version": 1,
        "pokemon": {
            "charizard": "리자몽",
            "riolu": "리오르",
            "totodile": "리아코",
            "garchomp": "한카리아스",
            "lapras": "라프라스",
        },
        "moves": {
            "tera-blast": "테라버스트",
            "flamethrower": "화염방사",
            "earthquake": "지진",
        },
        "abilities": {
            "blaze": "맹화",
            "rough-skin": "까칠한피부",
        },
        "types": {
            "fire": "불꽃",
        },
        "_unmapped": {
            "pokemon": [],
            "moves": [],
            "abilities": [],
            "types": [],
        },
        "_overridden": {
            "pokemon": [],
            "moves": ["tera-blast"],
            "abilities": [],
            "types": [],
        },
    }
    with mapping_path.open("w", encoding="utf-8") as file:
        json.dump(mapping, file, ensure_ascii=False)
    return mapping_path
