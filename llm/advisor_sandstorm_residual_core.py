"""Canonical pure Sandstorm residual decision shared by runtime and Turn Engine."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def evaluate_sandstorm_residual(*, current_type: Sequence[str], item: str | None, active_abilities: Mapping[str, str], target_side: str, current_hp: int, maximum_hp: int) -> dict[str, Any]:
    """Resolve only exact, already-authorized Sandstorm residual inputs."""
    if target_side not in {"self", "opponent"} or not _types(current_type) or not _item(item) or not _hp(current_hp, maximum_hp):
        return {"status": "incomplete", "reason": "canonical_sandstorm_authority"}
    if {"rock", "ground", "steel"} & set(current_type):
        return _complete(current_type, current_hp, maximum_hp, 0, "immune_by_type")
    if item == "safety-goggles":
        return _complete(current_type, current_hp, maximum_hp, 0, "prevented_by_safety_goggles")
    if not _abilities(active_abilities):
        return {"status": "incomplete", "reason": "canonical_sandstorm_authority"}
    abilities = set(active_abilities.values())
    if "neutralizing-gas" not in abilities and abilities & {"cloud-nine", "air-lock"}:
        return _complete(current_type, current_hp, maximum_hp, 0, "suppressed_by_ability")
    if "neutralizing-gas" not in abilities and active_abilities[target_side] in {"magic-guard", "overcoat", "sand-force", "sand-rush", "sand-veil"}:
        return _complete(current_type, current_hp, maximum_hp, 0, "immune_by_ability")
    return _complete(current_type, current_hp, maximum_hp, maximum_hp // 16, "damaged")


def _complete(current_type: Sequence[str], hp: int, maximum: int, damage: int, outcome: str) -> dict[str, Any]:
    post = max(0, hp - damage)
    return {"status": "complete", "current_type": list(current_type), "pre_hp": hp, "max_hp": maximum, "residual_damage": damage, "post_hp": post, "outcome": outcome, "guaranteed_ko": post == 0}


def _types(value: Sequence[str]) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and 1 <= len(value) <= 2 and all(isinstance(entry, str) and bool(entry) for entry in value)


def _item(value: Any) -> bool:
    return value is None or isinstance(value, str)


def _abilities(value: Mapping[str, str]) -> bool:
    return isinstance(value, Mapping) and set(value) == {"self", "opponent"} and all(isinstance(ability, str) and bool(ability) for ability in value.values())


def _hp(hp: Any, maximum: Any) -> bool:
    return all(isinstance(value, int) and not isinstance(value, bool) for value in (hp, maximum)) and maximum >= 1 and 0 <= hp <= maximum
