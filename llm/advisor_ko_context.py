"""Limited KO/OHKO/2HKO context helpers for LLM advisor payloads."""

from __future__ import annotations

from typing import Any


KO_CONTEXT_MODE = "limited_damage_roll_ko_context"
KO_CONTEXT_LIMITATIONS = [
    "Limited damage-roll context only.",
    "Accuracy, speed order, priority, recovery, hazards, chip damage, switching, protection, and turn sequencing are not modeled.",
]
TWO_HKO_ASSUMPTIONS = [
    "Same move used twice.",
    "No healing, recovery, chip damage, protection, switching, item survival integration, or turn sequencing is modeled.",
]


def build_ko_context(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    *,
    defender_key: str,
    scope: str,
) -> dict[str, Any]:
    base = {
        "mode": KO_CONTEXT_MODE,
        "scope": scope,
        "defender_side": defender_key,
        "raw_damage_rolls_changed": False,
        "is_final_battle_truth": False,
        "limitations": list(KO_CONTEXT_LIMITATIONS),
    }

    if not _damage_estimate_available(damage_estimate):
        return _unavailable(base, "damage_estimate_missing")

    hp_state = _target_hp_state(battle_input, damage_estimate, defender_key)
    if hp_state["status"] == "unknown":
        return _unavailable(base, "hp_unknown")
    current_hp = hp_state.get("current_hp")
    if not isinstance(current_hp, int) or current_hp <= 0:
        return _unavailable(base, "hp_unknown")

    damage_range = damage_estimate.get("damage_range")
    if not isinstance(damage_range, dict):
        return _unavailable(base, "damage_estimate_missing")
    min_damage = damage_range.get("min")
    max_damage = damage_range.get("max")
    if not isinstance(min_damage, int) or not isinstance(max_damage, int):
        return _unavailable(base, "damage_estimate_missing")

    rolls = damage_estimate.get("rolls")
    roll_values = [roll for roll in rolls if isinstance(roll, int)] if isinstance(rolls, list) else []
    ohko = _ohko_context(
        current_hp=current_hp,
        min_damage=min_damage,
        max_damage=max_damage,
        rolls=roll_values,
    )

    return {
        **base,
        "available": True,
        "target_hp": {
            "current_hp": current_hp,
            "max_hp": hp_state.get("max_hp"),
            "hp_percent": hp_state.get("hp_percent"),
            "source": hp_state.get("source"),
        },
        "damage": {
            "min": min_damage,
            "max": max_damage,
            "roll_count": len(roll_values),
        },
        "ohko": ohko,
        "two_hko": _two_hko_context(
            current_hp=current_hp,
            min_damage=min_damage,
            max_damage=max_damage,
        ),
    }


def _unavailable(base: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **base,
        "available": False,
        "reason": reason,
    }


def _damage_estimate_available(damage_estimate: dict[str, Any]) -> bool:
    if not isinstance(damage_estimate, dict):
        return False
    if damage_estimate.get("status") != "available_with_default_assumptions":
        return False
    return isinstance(damage_estimate.get("damage_range"), dict)


def _target_hp_state(
    battle_input: dict[str, Any],
    damage_estimate: dict[str, Any],
    defender_key: str,
) -> dict[str, Any]:
    defender = _pokemon_payload(battle_input, defender_key)
    exact_current_hp = _positive_int(defender.get("current_hp"))
    exact_max_hp = _positive_int(defender.get("max_hp"))
    if exact_current_hp is not None:
        return {
            "status": "known",
            "current_hp": exact_current_hp,
            "max_hp": exact_max_hp,
            "hp_percent": defender.get("hp_percent") if isinstance(defender.get("hp_percent"), int) else None,
            "source": "exact_current_hp",
        }

    hp_percent = defender.get("hp_percent")
    if hp_percent == 100:
        hp_reference = _defender_hp_reference(damage_estimate)
        if hp_reference is None:
            return {"status": "unknown"}
        return {
            "status": "known",
            "current_hp": hp_reference,
            "max_hp": hp_reference,
            "hp_percent": 100,
            "source": "full_hp_reference",
        }

    return {"status": "unknown"}


def _pokemon_payload(battle_input: dict[str, Any], role_key: str) -> dict[str, Any]:
    pokemon = battle_input.get("pokemon")
    if not isinstance(pokemon, dict):
        return {}
    payload = pokemon.get(role_key)
    return payload if isinstance(payload, dict) else {}


def _defender_hp_reference(damage_estimate: dict[str, Any]) -> int | None:
    derived_stats = damage_estimate.get("derived_stats")
    if not isinstance(derived_stats, dict):
        return None
    defender = derived_stats.get("defender")
    if not isinstance(defender, dict):
        return None
    return _positive_int(defender.get("default_max_hp"))


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _ohko_context(
    *,
    current_hp: int,
    min_damage: int,
    max_damage: int,
    rolls: list[int],
) -> dict[str, Any]:
    if rolls:
        successful_rolls = sum(1 for roll in rolls if roll >= current_hp)
        total_rolls = len(rolls)
        return {
            "possible": successful_rolls > 0,
            "guaranteed": successful_rolls == total_rolls,
            "chance": successful_rolls / total_rolls,
            "successful_rolls": successful_rolls,
            "total_rolls": total_rolls,
            "method": "roll_count",
        }

    guaranteed = min_damage >= current_hp
    possible = max_damage >= current_hp
    return {
        "possible": possible,
        "guaranteed": guaranteed,
        "chance": None,
        "successful_rolls": None,
        "total_rolls": 0,
        "method": "limited_min_max_no_rolls",
    }


def _two_hko_context(
    *,
    current_hp: int,
    min_damage: int,
    max_damage: int,
) -> dict[str, Any]:
    return {
        "possible": max_damage * 2 >= current_hp,
        "guaranteed": min_damage * 2 >= current_hp,
        "method": "limited_min_max",
        "assumptions": list(TWO_HKO_ASSUMPTIONS),
    }
