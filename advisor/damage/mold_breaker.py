from __future__ import annotations

from advisor.damage.abilities import AbilityEffect


MOLD_BREAKERS = frozenset({"mold-breaker", "teravolt", "turboblaze"})
MOLD_BREAKER_IMMUNE_ABILITIES = frozenset({"shadow-shield"})


def is_mold_breaker_active(attacker_ability_id: str | None) -> bool:
    return attacker_ability_id in MOLD_BREAKERS


def is_defender_ability_bypassed_by_mold_breaker(
    defender_ability: AbilityEffect | None,
    attacker_ability_id: str | None,
) -> bool:
    if defender_ability is None or not is_mold_breaker_active(attacker_ability_id):
        return False
    if defender_ability.ability_id in MOLD_BREAKER_IMMUNE_ABILITIES:
        return False
    return bool(defender_ability.raw_data.get("ignored_by_mold_breaker", True))


def is_neutralizing_gas_active(
    attacker_ability_id: str | None,
    defender_ability_id: str | None,
    ally_ability_ids: tuple[str | None, ...] = (),
) -> bool:
    if attacker_ability_id == "neutralizing-gas":
        return True
    if defender_ability_id == "neutralizing-gas":
        return True
    return any(ability_id == "neutralizing-gas" for ability_id in ally_ability_ids)


def effective_attacker_ability(
    attacker_ability: AbilityEffect | None,
    neutralizing_gas_active: bool,
) -> AbilityEffect | None:
    if attacker_ability is None:
        return None
    if neutralizing_gas_active and attacker_ability.ability_id != "neutralizing-gas":
        return None
    return attacker_ability


def effective_defender_ability(
    defender_ability: AbilityEffect | None,
    attacker_ability_id: str | None,
    neutralizing_gas_active: bool,
) -> AbilityEffect | None:
    if defender_ability is None:
        return None
    if neutralizing_gas_active and defender_ability.ability_id != "neutralizing-gas":
        return None
    if is_defender_ability_bypassed_by_mold_breaker(defender_ability, attacker_ability_id):
        return None
    return defender_ability
