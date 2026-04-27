from __future__ import annotations

import json
from pathlib import Path


CACHE_DIR = Path("data/cache/pokemon")


def test_charizard_base_stats() -> None:
    charizard = _load_entity("charizard")

    assert charizard["base_stats"] == {
        "hp": 78,
        "atk": 84,
        "def": 78,
        "spa": 109,
        "spd": 85,
        "spe": 100,
    }


def test_mega_charizard_y_ability() -> None:
    mega_y = _load_entity("charizard-mega-y")

    assert mega_y["abilities"] == [
        {"is_hidden": False, "name": "drought", "name_ko": "가뭄", "slot": 1}
    ]


def test_tauros_paldea_combat_type() -> None:
    tauros = _load_entity("tauros-paldea-combat-breed")

    assert tauros["types"] == ["fighting"]


def test_floette_eternal_exists() -> None:
    floette = _load_entity("floette-eternal")

    assert floette["availability"] == "transfer_only"
    assert floette["types"] == ["fairy"]


def test_all_entities_have_korean_names() -> None:
    index = _load_index()

    for entity_id in index:
        assert _load_entity(entity_id)["name"]["ko"]


def _load_index() -> dict[str, str]:
    with (CACHE_DIR / "_index.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_entity(entity_id: str) -> dict:
    with (CACHE_DIR / f"{entity_id}.json").open("r", encoding="utf-8") as file:
        return json.load(file)
