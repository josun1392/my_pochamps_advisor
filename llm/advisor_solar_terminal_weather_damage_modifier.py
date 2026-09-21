"""Bound Solar terminal weak-weather damage modifier authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle
from advisor.damage.q12 import Q12_ONE

SCHEMA_VERSION = "solar-terminal-weather-damage-modifier-authority-v1"
_SOLAR = frozenset({"solar-beam", "solar-blade"})
_WEAK = frozenset({"rain", "sandstorm", "snow"})


def materialize_solar_terminal_weather_damage_modifier_authority(
    *,
    move_id: str,
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action_id: str,
    source_state_fingerprint: str,
    actor_mechanics: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(move_id, str) or move_id not in _SOLAR:
        return None
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    if (
        lifecycle.get("status") != "resolved"
        or lifecycle.get("lifecycle_family") != "weather_sensitive_charge_then_damage"
        or lifecycle.get("weak_weather_damage_modifier_present") is not True
    ):
        return _result("rejected", "solar_terminal_modifier_lifecycle_invalid")
    field = actor_mechanics.get("field") if isinstance(actor_mechanics, Mapping) else None
    weather = field.get("weather") if isinstance(field, Mapping) and field.get("status") == "known" else None
    if not isinstance(weather, str) or weather == "unknown":
        return _result("incomplete", "solar_terminal_weather_unknown")
    weak = weather in _WEAK
    source_class = (
        ("raindance", "primordialsea") if weather == "rain"
        else ("sandstorm",) if weather == "sandstorm"
        else ("hail", "snowscape") if weather == "snow"
        else ("sunnyday", "desolateland") if weather == "sun"
        else ()
    )
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "move_id": move_id,
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action_id,
        "source_state_fingerprint": source_state_fingerprint,
        "terminal_weather": {
            "status": "known",
            "value": weather,
            "canonical_source_class": source_class,
        },
        "weak_weather": weak,
        "modifier_q12": Q12_ONE // 2 if weak else Q12_ONE,
        "modifier_fraction": {"numerator": 1, "denominator": 2} if weak else {"numerator": 1, "denominator": 1},
        "modifier_stage": "weather_modifier_after_generic_weather_before_critical",
        "provenance": "canonical_solar_terminal_weather_damage_modifier_v1",
    }


def validate_solar_terminal_weather_damage_modifier_authority(
    *,
    authority: Any,
    move_id: str,
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action_id: str,
    source_state_fingerprint: str,
    actor_mechanics: Mapping[str, Any],
) -> str | None:
    expected = materialize_solar_terminal_weather_damage_modifier_authority(
        move_id=move_id,
        actor=actor,
        target=target,
        action_id=action_id,
        source_state_fingerprint=source_state_fingerprint,
        actor_mechanics=actor_mechanics,
    )
    return None if isinstance(authority, Mapping) and authority == expected else "solar_terminal_weather_damage_modifier_authority_mismatch"


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
