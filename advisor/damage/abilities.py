from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.damage.q12 import Q12_ONE


ABILITIES_PATH = Path("data/static/abilities.json")
WEATHER_SUPPRESSORS = {"cloud-nine", "air-lock"}


@dataclass(frozen=True, slots=True)
class AbilityEffect:
    ability_id: str
    category: str
    implemented: bool
    weather: str | None = None
    terrain: str | None = None
    boosted_types: tuple[str, ...] = ()
    boosted_stats: tuple[str, ...] = ()
    multiplier_q12: int = Q12_ONE
    raw_data: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_abilities_catalog() -> dict[str, AbilityEffect]:
    raw = json.loads(ABILITIES_PATH.read_text(encoding="utf-8"))
    catalog: dict[str, AbilityEffect] = {}
    for ability_id, data in raw["abilities"].items():
        stat = data.get("stat")
        terrain = data.get("terrain")
        catalog[ability_id] = AbilityEffect(
            ability_id=ability_id,
            category=data["category"],
            implemented=bool(data.get("implemented", False)),
            weather=data.get("weather"),
            terrain=terrain if terrain in {"electric", "grassy", "misty", "psychic"} else None,
            boosted_types=tuple(data.get("boosted_types", [])),
            boosted_stats=(stat,) if isinstance(stat, str) else tuple(data.get("boosted_stats", [])),
            multiplier_q12=int(data.get("multiplier_q12", Q12_ONE)),
            raw_data=data,
        )
    return catalog


def get_ability(ability_id: str | None) -> AbilityEffect | None:
    if ability_id is None:
        return None
    return load_abilities_catalog().get(ability_id)


def is_weather_suppressed(
    attacker_ability: str | None,
    defender_ability: str | None,
) -> bool:
    return attacker_ability in WEATHER_SUPPRESSORS or defender_ability in WEATHER_SUPPRESSORS
