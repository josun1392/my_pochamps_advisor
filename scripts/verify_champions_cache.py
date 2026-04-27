from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import validate

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.cache_config import CACHE_DIR, POKEMON_CACHE_META  # noqa: E402


ROSTER_PATH = PROJECT_ROOT / "data" / "static" / "champions_roster.json"
STANDARD_TYPES = {
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
}

POKEMON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "entity_id",
        "species",
        "form_type",
        "pokeapi_id",
        "name",
        "types",
        "base_stats",
        "abilities",
        "weight_kg",
        "height_m",
        "movepool",
        "sprites",
        "fetched_at",
        "pokeapi_version",
    ],
    "properties": {
        "entity_id": {"type": "string", "minLength": 1},
        "species": {"type": "string", "minLength": 1},
        "form_type": {"enum": ["default", "form", "mega"]},
        "pokeapi_id": {"type": "integer"},
        "name": {
            "type": "object",
            "required": ["en", "ko"],
            "properties": {
                "en": {"type": "string", "minLength": 1},
                "ko": {"type": "string", "minLength": 1},
            },
        },
        "types": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string"}},
        "base_stats": {
            "type": "object",
            "required": ["hp", "atk", "def", "spa", "spd", "spe"],
            "additionalProperties": {"type": "integer"},
        },
        "abilities": {"type": "array"},
        "weight_kg": {"type": "number"},
        "height_m": {"type": "number"},
        "movepool": {
            "type": "object",
            "required": ["level_up", "machine", "tutor", "egg"],
        },
        "sprites": {"type": "object"},
        "fetched_at": {"type": "string"},
        "pokeapi_version": {"type": "string"},
    },
}


def main() -> int:
    roster = _load_json(ROSTER_PATH)
    expected_entities = _expected_entities(roster)
    index_path = CACHE_DIR / "_index.json"
    index = _load_json(index_path)
    assert set(index) == expected_entities

    total_size = 0
    for entity_id, relative_path in index.items():
        path = PROJECT_ROOT / relative_path
        assert path.exists(), f"missing cache file: {relative_path}"
        total_size += path.stat().st_size
        data = _load_json(path)
        validate(data, POKEMON_SCHEMA)
        assert data["entity_id"] == entity_id
        assert all(1 <= value <= 255 for value in data["base_stats"].values())
        assert all(type_name in STANDARD_TYPES for type_name in data["types"])
        assert data["name"]["ko"]

    assert POKEMON_CACHE_META.exists()
    print("cache verification passed")
    print(f"pokemon entities: {len(index)}")
    print(f"total cache size: {total_size / (1024 * 1024):.2f} MB")
    return 0


def _expected_entities(roster: dict[str, Any]) -> set[str]:
    entities: set[str] = set()
    for species in roster["species"]:
        for form in species["forms"]:
            if form.get("pokeapi_supported") is True:
                entities.add(form["form_id"])
        for mega in species["mega_evolutions"]:
            entities.add(mega["mega_id"])
    return entities


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    raise SystemExit(main())
