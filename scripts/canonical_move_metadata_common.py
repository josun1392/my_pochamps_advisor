from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from core.champions_move_overrides import ChampionsMoveOverrides

SOURCE_SCHEMA_VERSION = "champions-move-metadata-source-snapshot-v1"
CANONICAL_SCHEMA_VERSION = "canonical-move-metadata-v1"
PRIORITY_MIN = -7
PRIORITY_MAX = 7
_MOVE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file, object_pairs_hook=_unique_object)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def canonical_json_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def legal_move_set_sha256(move_ids: Iterable[str]) -> str:
    """Hash sorted unique move ids as UTF-8, one id per line, with a final newline."""
    normalized = sorted(set(move_ids))
    return sha256_bytes(("\n".join(normalized) + "\n").encode("utf-8"))


def validate_move_id(value: Any) -> str:
    if not isinstance(value, str) or not _MOVE_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid canonical move id: {value!r}")
    return value


def derive_champions_legal_move_ids(
    movepool_dir: Path,
    *,
    move_overrides: ChampionsMoveOverrides | None = None,
) -> list[str]:
    raw_ids: set[str] = set()
    fixtures = sorted(movepool_dir.glob("*.json"))
    if not fixtures:
        raise ValueError(f"No Champions movepool fixtures found: {movepool_dir}")
    for path in fixtures:
        data = load_json(path)
        moves = data.get("moves")
        if not isinstance(moves, list):
            raise ValueError(f"Champions fixture moves must be a list: {path}")
        for row in moves:
            if not isinstance(row, dict):
                raise ValueError(f"Champions move row must be an object: {path}")
            raw_ids.add(validate_move_id(row.get("move_id")))
    if not raw_ids:
        raise ValueError("Champions legal move set is empty")
    overrides = move_overrides or ChampionsMoveOverrides()
    return sorted(overrides.filter_allowed_move_ids(raw_ids))


def validate_priority(value: Any, *, move_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Priority must be an explicit integer for {move_id}: {value!r}")
    if not PRIORITY_MIN <= value <= PRIORITY_MAX:
        raise ValueError(f"Priority out of range for {move_id}: {value}")
    return value


def validate_pokeapi_id(value: Any, *, move_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Invalid PokeAPI id for {move_id}: {value!r}")
    return value


def records_by_move_id(records: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    result: dict[str, dict[str, Any]] = {}
    seen_ids: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("source record must be an object")
        move_id = validate_move_id(record.get("name"))
        pokeapi_id = validate_pokeapi_id(record.get("id"), move_id=move_id)
        if move_id in result:
            raise ValueError(f"Duplicate normalized move name: {move_id}")
        if pokeapi_id in seen_ids:
            raise ValueError(f"Duplicate normalized PokeAPI id: {pokeapi_id}")
        validate_priority(record.get("priority"), move_id=move_id)
        result[move_id] = record
        seen_ids.add(pokeapi_id)
    return result


def validate_exact_move_set(*, actual: Iterable[str], expected: Iterable[str], label: str) -> None:
    actual_set, expected_set = set(actual), set(expected)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if missing or extra:
        raise ValueError(f"{label} move-set mismatch: missing={missing[:20]} extra={extra[:20]}")


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_path.write_bytes(canonical_json_bytes(data))
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
