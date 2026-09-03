from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.damage.q12 import M_STAB, Q12_ONE
from advisor.damage.modifiers._q12 import MUL_1_3, MUL_2_0


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


# ``abilities.json`` is intentionally local/protected on this deployment.
# Keep the one production-ready mechanics addition code-owned until the static
# catalog can be updated through its separate data workflow.
_CANONICAL_ABILITY_OVERRIDES = {
    "sharpness": AbilityEffect(
        ability_id="sharpness",
        category="bp_modifier",
        implemented=True,
        multiplier_q12=M_STAB,
        raw_data={"condition": "slicing", "provenance": "canonical_sharpness_v1"},
    ),
    "analytic": AbilityEffect(
        ability_id="analytic",
        category="bp_modifier",
        implemented=True,
        multiplier_q12=MUL_1_3,
        raw_data={"condition": "exact_immediate_action_order_opponent_first", "provenance": "canonical_analytic_v1"},
    ),
    "stakeout": AbilityEffect(
        ability_id="stakeout",
        category="stat_multiplier",
        implemented=True,
        multiplier_q12=MUL_2_0,
        raw_data={"condition": "exact_same_turn_opponent_switch_target", "provenance": "canonical_stakeout_v1"},
    ),
}


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
    return _CANONICAL_ABILITY_OVERRIDES.get(ability_id, load_abilities_catalog().get(ability_id))


def is_weather_suppressed(
    attacker_ability: str | None,
    defender_ability: str | None,
) -> bool:
    return attacker_ability in WEATHER_SUPPRESSORS or defender_ability in WEATHER_SUPPRESSORS
