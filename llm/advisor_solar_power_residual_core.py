"""Canonical pure Solar Power Sun residual decision shared by runtime and Turn Engine."""
from __future__ import annotations

from typing import Any, Mapping


def evaluate_solar_power_residual(*, active_abilities: Mapping[str, str], target_side: str, current_hp: int, maximum_hp: int) -> dict[str, Any]:
    if target_side not in {"self", "opponent"} or not isinstance(active_abilities, Mapping) or set(active_abilities) != {"self", "opponent"} or any(not isinstance(value, str) or not value for value in active_abilities.values()) or active_abilities[target_side] != "solar-power" or not all(isinstance(value, int) and not isinstance(value, bool) for value in (current_hp, maximum_hp)) or maximum_hp < 1 or not 0 <= current_hp <= maximum_hp:
        return {"status": "incomplete", "reason": "canonical_solar_power_authority"}
    abilities = set(active_abilities.values())
    if "neutralizing-gas" in abilities:
        return {"status": "complete", "outcome": "suppressed_by_neutralizing_gas"}
    if abilities & {"cloud-nine", "air-lock"}:
        return {"status": "complete", "outcome": "suppressed_by_weather_ability"}
    damage = maximum_hp // 8
    post_hp = max(0, current_hp - damage)
    return {"status": "complete", "pre_hp": current_hp, "max_hp": maximum_hp, "damage": damage, "post_hp": post_hp, "outcome": "damaged", "guaranteed_ko": post_hp == 0}
