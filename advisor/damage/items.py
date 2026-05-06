from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from advisor.damage.q12 import Q12_ONE


ITEMS_PATH = Path("data/static/items_damage.json")
MEGA_STONES_PATH = Path("data/static/mega_stones.json")


@dataclass(frozen=True, slots=True)
class ItemEffect:
    item_id: str
    kind: str
    boosted_types: tuple[str, ...] = ()
    boosted_stats: tuple[str, ...] = ()
    multiplier_q12: int = Q12_ONE
    species_lock: tuple[str, ...] = ()
    requires_nfe: bool = False
    requires_super_effective: bool = False
    untransformed_only: bool = False
    always_resist: bool = False


@lru_cache(maxsize=1)
def load_items_catalog() -> dict[str, ItemEffect]:
    raw = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    catalog: dict[str, ItemEffect] = {}

    for item_id, data in raw["type_boost_items"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="type_boost",
            boosted_types=(data["type"],),
            multiplier_q12=data["multiplier_q12"],
        )

    for item_id, data in raw["type_plates"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="type_plate",
            boosted_types=(data["type"],),
            multiplier_q12=data["multiplier_q12"],
        )

    for item_id, data in raw["species_orbs"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="species_orb",
            boosted_types=tuple(data["boosted_types"]),
            multiplier_q12=data["multiplier_q12"],
            species_lock=tuple(data["species"]),
        )

    for item_id, data in raw["stat_boost_items"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="stat_boost",
            boosted_stats=(data["stat"],),
            multiplier_q12=data["multiplier_q12"],
            requires_super_effective=data["stat"] == "super_effective_only",
        )

    for item_id, data in raw["defensive_items"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="defensive",
            boosted_stats=tuple(data["stats"]),
            multiplier_q12=data["multiplier_q12"],
            requires_nfe=bool(data.get("requires_nfe", False)),
        )

    for item_id, data in raw["species_stat_items"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="species_stat",
            boosted_stats=tuple(data["stats"]),
            multiplier_q12=data["multiplier_q12"],
            species_lock=tuple(data["species"]),
            untransformed_only=bool(data.get("untransformed_only", False)),
        )

    for item_id, data in raw["type_resist_berries"].items():
        catalog[item_id] = ItemEffect(
            item_id=item_id,
            kind="type_resist_berry",
            boosted_types=(data["resist_type"],),
            multiplier_q12=2048,
            always_resist=bool(data.get("always_resist", False)),
        )

    return catalog


def get_item(item_id: str | None) -> ItemEffect | None:
    if item_id is None:
        return None
    return load_items_catalog().get(item_id)


@lru_cache(maxsize=1)
def load_mega_stones() -> dict[str, Any]:
    return json.loads(MEGA_STONES_PATH.read_text(encoding="utf-8"))


def is_mega_stone(item_id: str | None) -> bool:
    if item_id is None:
        return False
    stones = load_mega_stones()
    return item_id in stones["mega_stones"] or item_id in stones["primal_orbs"]


def get_mega_form(item_id: str, base_species: str) -> str | None:
    stones = load_mega_stones()
    if item_id in stones["mega_stones"]:
        entry = stones["mega_stones"][item_id]
        if entry["base"] == base_species:
            return entry["mega_form"]
    if item_id in stones["primal_orbs"]:
        entry = stones["primal_orbs"][item_id]
        if entry["base"] == base_species:
            return entry["primal_form"]
    rayquaza = stones.get("rayquaza_mega", {})
    if item_id == "dragon-ascent" and rayquaza.get("base") == base_species:
        return rayquaza.get("mega_form")
    return None
