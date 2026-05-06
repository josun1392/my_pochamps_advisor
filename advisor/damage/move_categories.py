"""Move flag/secondary loader for ability damage modifiers."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_move_flags() -> dict:
    path = Path(__file__).parent.parent.parent / "data" / "static" / "move_flags.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_move_flags(move_id: str) -> tuple[str, ...]:
    data = load_move_flags()
    return tuple(data.get("flags_by_move", {}).get(move_id, []))


def has_secondary_effect(move_id: str) -> bool:
    data = load_move_flags()
    return move_id in data.get("secondary_effect_moves", [])
