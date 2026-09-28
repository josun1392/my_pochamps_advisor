from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CANONICAL_MOVE_METADATA_PATH = Path("data/static/canonical_move_metadata_v1.json")
SCHEMA_VERSION = "canonical-move-metadata-v1"
PRIORITY_MIN = -7
PRIORITY_MAX = 7


class CanonicalMoveMetadataRepository:
    """Offline canonical base move metadata owner.

    V1 exposes only explicit base priority.  It never performs network I/O,
    infers defaults, or decides Pokemon-specific legality.
    """

    def __init__(self, path: Path = DEFAULT_CANONICAL_MOVE_METADATA_PATH) -> None:
        self.path = path
        self._moves = self._load(path)

    def get_priority(self, move_id: str) -> int:
        row = self._moves.get(move_id)
        if not isinstance(row, dict):
            raise RuntimeError(f"Canonical move priority is unavailable: {move_id}")
        return _priority(row.get("priority"), move_id=move_id)

    @staticmethod
    def _load(path: Path) -> dict[str, dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file, object_pairs_hook=_unique_object)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"Canonical move metadata could not be loaded: {path}") from exc

        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported canonical move metadata schema: {path}")
        moves = data.get("moves")
        if not isinstance(moves, dict):
            raise RuntimeError(f"Canonical move metadata moves are missing: {path}")

        validated: dict[str, dict[str, Any]] = {}
        for move_id, row in moves.items():
            if not isinstance(move_id, str) or not move_id or not isinstance(row, dict):
                raise RuntimeError(f"Malformed canonical move metadata row: {move_id!r}")
            _priority(row.get("priority"), move_id=move_id)
            validated[move_id] = row
        return validated


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _priority(value: Any, *, move_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"Canonical move priority must be an explicit integer: {move_id}")
    if not PRIORITY_MIN <= value <= PRIORITY_MAX:
        raise RuntimeError(f"Canonical move priority is out of range: {move_id}={value}")
    return value
