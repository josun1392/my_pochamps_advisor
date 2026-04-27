from __future__ import annotations

import json
import logging
from pathlib import Path

from core.ko_form_rules import apply_korean_form, split_pokemon_name
from core.ko_mapping_loader import KoMappingLoader
from scripts.build_ko_mapping import _empty_mapping, _resolve_ko_name


def test_split_pokemon_name_simple() -> None:
    assert split_pokemon_name("charizard") == ("charizard", "")


def test_split_pokemon_name_single_form() -> None:
    assert split_pokemon_name("landorus-therian") == ("landorus", "therian")


def test_split_pokemon_name_compound_form() -> None:
    assert split_pokemon_name("urshifu-rapid-strike") == ("urshifu", "rapid-strike")


def test_apply_korean_form_with_paren() -> None:
    assert apply_korean_form("랜드로스", "therian") == "랜드로스(영물폼)"


def test_apply_korean_form_with_space() -> None:
    assert apply_korean_form("리자몽", "mega-x") == "리자몽 (메가X)"


def test_apply_korean_form_unknown_suffix(caplog) -> None:
    caplog.set_level(logging.WARNING)

    assert apply_korean_form("테스트몬", "unknown-form") == "테스트몬-unknown-form"
    assert "알 수 없는 포켓몬 폼 접미사" in caplog.text


def test_loader_get_pokemon_ko(tmp_path: Path) -> None:
    loader = KoMappingLoader(_write_fixture_mapping(tmp_path))

    assert loader.get_pokemon_ko("charizard") == "리자몽"


def test_loader_reverse_lookup(tmp_path: Path) -> None:
    loader = KoMappingLoader(_write_fixture_mapping(tmp_path))

    assert loader.get_pokemon_en("리자몽") == "charizard"


def test_loader_missing_returns_none(tmp_path: Path) -> None:
    loader = KoMappingLoader(_write_fixture_mapping(tmp_path))

    assert loader.get_pokemon_ko("missingno") is None
    assert loader.get_move_ko("missing-move") is None
    assert loader.get_ability_ko("missing-ability") is None
    assert loader.get_type_ko("missing-type") is None
    assert loader.get_pokemon_en("없는몬") is None


def test_manual_override_applied_when_pokeapi_missing() -> None:
    mapping = _empty_mapping()
    data = {
        "name": "tera-blast",
        "names": {
            "en": "Tera Blast",
        },
    }

    assert _resolve_ko_name(mapping, "moves", "tera-blast", data) == "테라버스트"


def test_manual_override_recorded_in_overridden_field() -> None:
    mapping = _empty_mapping()
    data = {
        "name": "tera-blast",
        "names": {
            "en": "Tera Blast",
        },
    }

    _resolve_ko_name(mapping, "moves", "tera-blast", data)

    assert mapping["_overridden"]["moves"] == ["tera-blast"]
    assert mapping["_unmapped"]["moves"] == []


def _write_fixture_mapping(tmp_path: Path) -> Path:
    mapping_path = tmp_path / "ko_mapping.json"
    mapping = {
        "_built_at": "2026-04-27T10:30:00Z",
        "_version": 1,
        "pokemon": {
            "charizard": "리자몽",
            "garchomp": "한카리아스",
        },
        "moves": {
            "flamethrower": "화염방사",
        },
        "abilities": {
            "blaze": "맹화",
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
            "moves": [],
            "abilities": [],
            "types": [],
        },
    }
    with mapping_path.open("w", encoding="utf-8") as file:
        json.dump(mapping, file, ensure_ascii=False)
    return mapping_path
