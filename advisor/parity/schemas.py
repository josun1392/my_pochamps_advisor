from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SchemaVersion = Literal["v1"]
Status = Literal["brn", "par", "slp", "frz", "psn", "tox"]
Weather = Literal[
    "sun",
    "harsh-sunlight",
    "rain",
    "heavy-rain",
    "sand",
    "hail",
    "snow",
    "strong-winds",
    "harsh_sunshine",
    "heavy_rain",
    "strong_winds",
]
Terrain = Literal["electric", "grassy", "misty", "psychic"]
Format = Literal["gen9ou", "gen9doubles"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Stats(StrictModel):
    hp: int = Field(ge=0)
    atk: int = Field(ge=0)
    def_: int = Field(alias="def", ge=0)
    spa: int = Field(ge=0)
    spd: int = Field(ge=0)
    spe: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Boosts(StrictModel):
    atk: int = Field(ge=-6, le=6)
    def_: int = Field(alias="def", ge=-6, le=6)
    spa: int = Field(ge=-6, le=6)
    spd: int = Field(ge=-6, le=6)
    spe: int = Field(ge=-6, le=6)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PokemonInput(StrictModel):
    species: str
    level: int = Field(ge=1, le=100)
    ability: str | None
    item: str | None
    nature: str
    evs: Stats
    ivs: Stats
    boosts: Boosts
    status: Status | None
    tera_type: str | None
    is_terastallized: bool
    boosted_stat: Literal["atk", "def", "spa", "spd", "spe", "auto"] | None = None


class DefenderInput(PokemonInput):
    current_hp_pct: int = Field(ge=0, le=100)


class MoveInput(StrictModel):
    name: str
    is_critical: bool
    is_z: bool
    is_max: bool


class SideInput(StrictModel):
    reflect: bool = False
    light_screen: bool = False
    aurora_veil: bool = False


class FieldInput(StrictModel):
    weather: Weather | None
    terrain: Terrain | None
    is_gravity: bool
    is_trick_room: bool
    format: Format
    ally_has_plus_minus: bool = False
    attacker_side: SideInput | None = None
    defender_side: SideInput | None = None


class DamageRequest(StrictModel):
    schema_version: SchemaVersion
    attacker: PokemonInput
    defender: DefenderInput
    move: MoveInput
    field: FieldInput


class KOChance(StrictModel):
    n_hits: int = Field(ge=0)
    chance: float = Field(ge=0.0, le=1.0)
    description: str


class Modifiers(StrictModel):
    stab: float
    weather: float
    type_effectiveness: float
    burn: float
    screens: float
    item: float
    ability_attacker: float
    ability_defender: float


class DamageResponse(StrictModel):
    schema_version: SchemaVersion
    damage_rolls: list[int]
    damage_min: int = Field(ge=0)
    damage_max: int = Field(ge=0)
    damage_min_pct: float = Field(ge=0.0)
    damage_max_pct: float = Field(ge=0.0)
    ko_chance: KOChance
    modifiers: Modifiers
    raw_calc_desc: str
