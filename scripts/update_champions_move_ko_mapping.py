from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ko_manual_overrides import MANUAL_OVERRIDES  # noqa: E402


MOVEPOOL_DIR = PROJECT_ROOT / "data" / "cache" / "champions" / "regulation_m_a" / "pokemon_movepools"
MAPPING_PATH = PROJECT_ROOT / "data" / "ko_mapping.json"
POKEAPI_MOVE_URL = "https://pokeapi.co/api/v2/move/{move_id}/"


def main() -> int:
    mapping = _load_json(MAPPING_PATH)
    move_names = _champions_move_names()
    session = requests.Session()
    session.headers.update({"User-Agent": "PokemonCopilot/0.1 Champions Korean move mapping"})

    unresolved: list[str] = []
    overrides = MANUAL_OVERRIDES.get("moves", {})
    for move_id in sorted(move_names):
        ko_name = _pokeapi_ko_name(session, move_id)
        if ko_name is None:
            ko_name = overrides.get(move_id)
            if ko_name is not None:
                _mark(mapping, "_overridden", "moves", move_id)
        if ko_name is None:
            unresolved.append(move_id)
            _mark(mapping, "_unmapped", "moves", move_id)
            continue
        mapping.setdefault("moves", {})[move_id] = ko_name
        _unmark(mapping, "_unmapped", "moves", move_id)
        time.sleep(0.02)

    mapping["_built_at"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _write_json(MAPPING_PATH, mapping)
    print(f"Champions moves: {len(move_names)}")
    print(f"Mapped moves: {len(mapping.get('moves', {}))}")
    print(f"Unresolved Champions moves: {len(unresolved)}")
    if unresolved:
        print(", ".join(unresolved))
        return 1
    return 0


def _champions_move_names() -> dict[str, str]:
    move_names: dict[str, str] = {}
    for path in MOVEPOOL_DIR.glob("*.json"):
        data = _load_json(path)
        for item in data.get("moves", []):
            if not isinstance(item, dict):
                continue
            move_id = item.get("move_id")
            name_en = item.get("name_en")
            if isinstance(move_id, str) and move_id and isinstance(name_en, str) and name_en:
                move_names.setdefault(move_id, name_en)
    return move_names


def _pokeapi_ko_name(session: requests.Session, move_id: str) -> str | None:
    response = session.get(POKEAPI_MOVE_URL.format(move_id=move_id), timeout=15)
    response.raise_for_status()
    data = response.json()
    for item in data.get("names", []):
        if item.get("language", {}).get("name") == "ko":
            value = item.get("name")
            return value if isinstance(value, str) and value else None
    return None


def _mark(mapping: dict[str, Any], section: str, category: str, value: str) -> None:
    entries = mapping.setdefault(section, {}).setdefault(category, [])
    if value not in entries:
        entries.append(value)
        entries.sort()


def _unmark(mapping: dict[str, Any], section: str, category: str, value: str) -> None:
    entries = mapping.setdefault(section, {}).setdefault(category, [])
    if value in entries:
        entries.remove(value)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
