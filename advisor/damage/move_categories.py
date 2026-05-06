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


def is_secondary_suppressed_by(
    move_id: str,
    *,
    attacker_ability: str | None,
    attacker_item: str | None = None,
) -> bool:
    """Return whether a move's built-in secondary effect is suppressed.

    This is a turn-engine predicate: it does not model item-added effects such
    as King's Rock flinch chances, and it does not mutate battle state.
    """
    del attacker_item
    return attacker_ability == "sheer-force" and has_secondary_effect(move_id)
