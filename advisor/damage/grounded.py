from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from advisor.damage.field import Field


@dataclass(frozen=True, slots=True)
class GroundedInputs:
    types: tuple[str, ...]
    ability: str | None = None
    item: str | None = None
    is_magnet_rise: bool = False
    is_telekinesis: bool = False
    is_smack_down: bool = False
    is_rooting: bool = False
    is_ingrain: bool = False


def is_grounded(inputs: GroundedInputs, field: Field) -> bool:
    item = _normalize(inputs.item)
    ability = _normalize(inputs.ability)
    if item == "iron-ball" or inputs.is_smack_down or inputs.is_ingrain:
        return True
    if field.is_gravity:
        return True
    if "flying" in inputs.types and not inputs.is_rooting:
        return False
    if ability == "levitate":
        return False
    if item == "air-balloon":
        return False
    if inputs.is_magnet_rise or inputs.is_telekinesis:
        return False
    return True


def _normalize(value: str | None) -> str | None:
    return None if value is None else value.lower().replace(" ", "-")
