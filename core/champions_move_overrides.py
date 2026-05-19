from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ChampionsMoveOverrides:
    def __init__(self, path: Path = Path("data/static/champions_move_overrides.json")) -> None:
        self.path = path
        self._data = self._load_data(path)

    def denied_move_ids(self) -> set[str]:
        denied_moves = self._data.get("global_denied_moves")
        if not isinstance(denied_moves, dict):
            return set()
        return {move_id for move_id in denied_moves if isinstance(move_id, str) and move_id}

    def is_denied(self, move_id: str) -> bool:
        return move_id in self.denied_move_ids()

    def filter_allowed_move_ids(self, move_ids: set[str]) -> set[str]:
        return set(move_ids) - self.denied_move_ids()

    def metadata_for(self, move_id: str) -> dict[str, Any] | None:
        denied_moves = self._data.get("global_denied_moves")
        if not isinstance(denied_moves, dict):
            return None
        metadata = denied_moves.get(move_id)
        return metadata if isinstance(metadata, dict) else None

    @staticmethod
    def _load_data(path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}
