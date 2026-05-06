from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal


Weather = Literal[
    "none",
    "sun",
    "harsh-sunlight",
    "rain",
    "heavy-rain",
    "sand",
    "snow",
    "strong-winds",
]

Terrain = Literal["none", "electric", "grassy", "misty", "psychic"]

WEATHERS: set[str] = {
    "none",
    "sun",
    "harsh-sunlight",
    "rain",
    "heavy-rain",
    "sand",
    "snow",
    "strong-winds",
}
TERRAINS: set[str] = {"none", "electric", "grassy", "misty", "psychic"}


@dataclass(frozen=True, slots=True)
class SideField:
    reflect: bool = False
    light_screen: bool = False
    aurora_veil: bool = False
    spikes: int = 0
    toxic_spikes: int = 0
    stealth_rock: bool = False
    sticky_web: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.spikes <= 3:
            raise ValueError("spikes must be between 0 and 3")
        if not 0 <= self.toxic_spikes <= 2:
            raise ValueError("toxic_spikes must be between 0 and 2")


@dataclass(frozen=True, slots=True)
class Field:
    weather: Weather = "none"
    terrain: Terrain = "none"
    is_doubles: bool = True
    is_gravity: bool = False
    is_magic_room: bool = False
    is_wonder_room: bool = False
    ally_has_plus_minus: bool = False
    attacker_side: SideField = field(default_factory=SideField)
    defender_side: SideField = field(default_factory=SideField)

    def __post_init__(self) -> None:
        if self.weather not in WEATHERS:
            raise ValueError(f"unsupported weather: {self.weather}")
        if self.terrain not in TERRAINS:
            raise ValueError(f"unsupported terrain: {self.terrain}")

    def with_weather(self, weather: Weather) -> Field:
        return replace(self, weather=weather)

    def with_terrain(self, terrain: Terrain) -> Field:
        return replace(self, terrain=terrain)
