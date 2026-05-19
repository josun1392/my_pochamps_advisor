from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.champions_move_overrides import ChampionsMoveOverrides


@dataclass(frozen=True)
class ChampionsMovePool:
    pokemon_id: str
    moves: list[str]
    status: str = "available"


class ChampionsMovePoolRepository:
    def __init__(
        self,
        cache_dir: Path = Path("data/cache/champions/regulation_m_a/pokemon_movepools"),
        move_overrides: ChampionsMoveOverrides | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.move_overrides = move_overrides or ChampionsMoveOverrides()

    def load_champions_movepool(self, pokemon_id: str) -> ChampionsMovePool | None:
        data = self._load_fixture(pokemon_id)
        if data is None:
            return None
        moves = self._move_ids(data.get("moves"))
        allowed_moves = sorted(self.move_overrides.filter_allowed_move_ids(set(moves)))
        return ChampionsMovePool(pokemon_id=pokemon_id, moves=allowed_moves)

    def get_allowed_move_ids_for_pokemon(self, pokemon_id: str) -> set[str]:
        pool = self.load_champions_movepool(pokemon_id)
        if pool is None:
            return set()
        return set(pool.moves)

    def filter_champions_moves_for_pokemon(
        self,
        pokemon_id: str,
        candidate_move_ids: set[str],
    ) -> set[str]:
        allowed_move_ids = self.get_allowed_move_ids_for_pokemon(pokemon_id)
        if not allowed_move_ids:
            return set()
        return set(candidate_move_ids) & allowed_move_ids

    def status_for_pokemon(self, pokemon_id: str) -> dict[str, str]:
        if self._fixture_path(pokemon_id).exists():
            return {"status": "available", "pokemon_id": pokemon_id}
        return {
            "status": "unavailable_missing_champions_movepool",
            "pokemon_id": pokemon_id,
            "reason": "No Serebii-derived Champions move pool fixture/cache exists for this Pokemon.",
        }

    def _load_fixture(self, pokemon_id: str) -> dict[str, Any] | None:
        path = self._fixture_path(pokemon_id)
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _fixture_path(self, pokemon_id: str) -> Path:
        return self.cache_dir / f"{pokemon_id}.json"

    @staticmethod
    def _move_ids(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        move_ids: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, dict):
                continue
            move_id = item.get("move_id")
            if isinstance(move_id, str) and move_id and move_id not in seen:
                move_ids.append(move_id)
                seen.add(move_id)
        return move_ids
