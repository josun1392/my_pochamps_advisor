"""Status effects on stats (Burn / Frostbite / Paralysis). Q12 fixed-point."""
from typing import Literal

Status = Literal[
    "healthy", "burn", "frostbite", "paralysis",
    "sleep", "freeze", "poison", "toxic"
]

Q12_ONE = 4096
Q12_HALF = 2048


def burn_atk_modifier(status: Status, ability_id: str) -> int:
    if status == "burn" and ability_id != "guts":
        return Q12_HALF
    return Q12_ONE


def frostbite_spa_modifier(status: Status) -> int:
    if status == "frostbite":
        return Q12_HALF
    return Q12_ONE


def paralysis_spe_modifier(status: Status, ability_id: str) -> int:
    if status == "paralysis" and ability_id != "quick-feet":
        return Q12_HALF
    return Q12_ONE


def is_status_active(status: Status) -> bool:
    return status != "healthy"
