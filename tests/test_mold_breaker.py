from __future__ import annotations

from advisor.damage.abilities import get_ability
from advisor.damage.mold_breaker import (
    effective_attacker_ability,
    effective_defender_ability,
    is_mold_breaker_active,
    is_neutralizing_gas_active,
)


def test_mold_breaker_family_detection() -> None:
    assert is_mold_breaker_active("mold-breaker")
    assert is_mold_breaker_active("teravolt")
    assert is_mold_breaker_active("turboblaze")
    assert not is_mold_breaker_active("tinted-lens")


def test_mold_breaker_suppresses_defender_ability() -> None:
    assert effective_defender_ability(
        get_ability("volt-absorb"),
        "mold-breaker",
        neutralizing_gas_active=False,
    ) is None


def test_neutralizing_gas_suppresses_other_abilities() -> None:
    assert is_neutralizing_gas_active("neutralizing-gas", None)
    assert effective_attacker_ability(
        get_ability("volt-absorb"),
        neutralizing_gas_active=True,
    ) is None
    assert effective_defender_ability(
        get_ability("volt-absorb"),
        None,
        neutralizing_gas_active=True,
    ) is None


def test_neutralizing_gas_holder_keeps_own_ability() -> None:
    neutralizing_gas = get_ability("neutralizing-gas")
    assert effective_attacker_ability(neutralizing_gas, True) == neutralizing_gas
    assert effective_defender_ability(neutralizing_gas, None, True) == neutralizing_gas
