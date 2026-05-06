from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from advisor.damage.abilities import AbilityEffect


MOVE_FLAGS_PATH = Path("data/static/move_flags.json")

TYPE_IMMUNITIES = {
    "volt-absorb": "electric",
    "water-absorb": "water",
    "flash-fire": "fire",
    "sap-sipper": "grass",
    "motor-drive": "electric",
    "lightning-rod": "electric",
    "storm-drain": "water",
    "earth-eater": "ground",
    "well-baked-body": "fire",
    "dry-skin": "water",
}


@lru_cache(maxsize=1)
def load_move_flags() -> dict[str, tuple[str, ...]]:
    raw = json.loads(MOVE_FLAGS_PATH.read_text(encoding="utf-8"))
    return {
        move_id: tuple(flags)
        for move_id, flags in raw.get("flags_by_move", {}).items()
    }


def move_flags_for(move_id: str) -> tuple[str, ...]:
    return load_move_flags().get(move_id, ())


def is_immune_by_ability(
    move_type: str,
    move_id: str,
    move_flags: tuple[str, ...],
    defender_ability: AbilityEffect | None,
    defender_grounded: bool,
    mold_breaker_active: bool,
) -> bool:
    if defender_ability is None or not defender_ability.implemented:
        return False
    if mold_breaker_active and defender_ability.raw_data.get("ignored_by_mold_breaker", True):
        return False

    ability_id = defender_ability.ability_id
    immune_type = TYPE_IMMUNITIES.get(ability_id)
    if immune_type == move_type:
        return True

    if ability_id == "levitate" and move_type == "ground" and not defender_grounded:
        return True

    if ability_id == "bulletproof" and "bullet" in move_flags:
        return True
    if ability_id == "soundproof" and "sound" in move_flags and move_id != "clangorous-soul":
        return True
    if ability_id == "overcoat" and "powder" in move_flags:
        return True

    return False


def is_wonder_guard_blocked(
    type_effectiveness: float,
    defender_ability: AbilityEffect | None,
    mold_breaker_active: bool,
) -> bool:
    if defender_ability is None or defender_ability.ability_id != "wonder-guard":
        return False
    if mold_breaker_active:
        return False
    return type_effectiveness <= 1.0
