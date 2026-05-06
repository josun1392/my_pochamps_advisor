from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Final


TYPES: Final[tuple[str, ...]] = (
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
)

TYPE_CHART_PATH = Path("data/static/type_chart_gen9.json")


@lru_cache(maxsize=1)
def load_type_chart() -> dict[str, dict[str, float]]:
    data = json.loads(TYPE_CHART_PATH.read_text(encoding="utf-8"))
    return data["chart"]


def type_effectiveness(
    move_type: str,
    defender_types: tuple[str, ...],
    chart: dict[str, dict[str, float]] | None = None,
) -> int:
    resolved_chart = chart or load_type_chart()
    multiplier = 1.0
    for defender_type in defender_types:
        multiplier *= resolved_chart[move_type][defender_type]
    if multiplier == 0.0:
        return 0
    return round(multiplier * 4096)


def type_effectiveness_multiplier(
    move_type: str,
    defender_types: tuple[str, ...],
    chart: dict[str, dict[str, float]] | None = None,
) -> float:
    resolved_chart = chart or load_type_chart()
    multiplier = 1.0
    for defender_type in defender_types:
        multiplier *= resolved_chart[move_type][defender_type]
    return multiplier
