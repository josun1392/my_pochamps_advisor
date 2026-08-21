"""Canonical pure Ice Body recovery decision shared by runtime and Turn Engine."""
from __future__ import annotations

from typing import Any, Mapping


def evaluate_ice_body_recovery(*, active_abilities: Mapping[str, str], target_side: str, current_hp: int, maximum_hp: int) -> dict[str, Any]:
    """Resolve only exact, already-authorized Ice Body recovery inputs."""
    return evaluate_weather_recovery(active_abilities=active_abilities, target_side=target_side, required_ability="ice-body", current_hp=current_hp, maximum_hp=maximum_hp)


def evaluate_weather_recovery(*, active_abilities: Mapping[str, str], target_side: str, required_ability: str, current_hp: int, maximum_hp: int) -> dict[str, Any]:
    """Resolve the approved Ice Body/Rain Dish/Dry Skin Rain recovery primitive only."""
    if target_side not in {"self", "opponent"} or required_ability not in {"ice-body", "rain-dish", "dry-skin"} or not _abilities(active_abilities) or active_abilities[target_side] != required_ability or not _hp(current_hp, maximum_hp):
        return {"status": "incomplete", "reason": "canonical_ice_body_authority"}
    abilities = set(active_abilities.values())
    if "neutralizing-gas" in abilities:
        return {"status": "complete", "outcome": "suppressed_by_neutralizing_gas"}
    if abilities & {"cloud-nine", "air-lock"}:
        return {"status": "complete", "outcome": "suppressed_by_weather_ability"}
    recovery = maximum_hp // (8 if required_ability == "dry-skin" else 16) if current_hp < maximum_hp else 0
    return {"status": "complete", "pre_hp": current_hp, "max_hp": maximum_hp, "recovery": recovery, "post_hp": min(maximum_hp, current_hp + recovery), "outcome": "recovered" if recovery else "already_full_hp"}


def _abilities(value: Mapping[str, str]) -> bool:
    return isinstance(value, Mapping) and set(value) == {"self", "opponent"} and all(isinstance(ability, str) and bool(ability) for ability in value.values())


def _hp(hp: Any, maximum: Any) -> bool:
    return all(isinstance(value, int) and not isinstance(value, bool) for value in (hp, maximum)) and maximum >= 1 and 0 <= hp <= maximum
