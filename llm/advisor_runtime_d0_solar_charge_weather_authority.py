"""Strict current-D0 Solar charge weather decision authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle
from llm.advisor_runtime_strategy_d0 import (
    _native_field_state,
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)

SCHEMA_VERSION = "runtime-d0-solar-charge-weather-decision-authority-v1"
_SOLAR = frozenset({"solar-beam", "solar-blade"})
_SUN = frozenset({"sun"})
_WEAK = frozenset({"rain", "sandstorm", "snow"})


def freeze_runtime_d0_solar_charge_weather_decision_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(strategy_d0, Mapping)
        or strategy_d0.get("status") != "resolved"
        or actor != strategy_d0.get("decision_owner")
        or not isinstance(action, Mapping)
        or action.get("action_type") != "attack"
        or not isinstance(action.get("identity"), str)
        or action.get("identity") not in _SOLAR
    ):
        return _result("rejected", "solar_weather_identity_or_d0_invalid")
    active = strategy_d0.get("active_owners")
    if (
        not isinstance(active, Mapping)
        or active.get(actor.get("side")) != dict(actor)
        or active.get(target.get("side")) != dict(target)
        or actor.get("side") == target.get("side")
    ):
        return _result("rejected", "solar_weather_active_owner_binding_invalid")
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"))

    metadata = resolve_runtime_d0_selectable_move_metadata_authority(
        strategy_d0=strategy_d0, action=action,
    )
    if metadata.get("status") != "resolved":
        return _result(
            "rejected" if metadata.get("status") == "rejected" else "incomplete",
            metadata.get("reason", "solar_weather_move_metadata_unavailable"),
        )
    move_id = action["identity"]
    if metadata.get("metadata", {}).get("move_id") != move_id:
        return _result("rejected", "solar_weather_move_metadata_mismatch")

    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    if (
        lifecycle.get("status") != "resolved"
        or lifecycle.get("lifecycle_family") != "weather_sensitive_charge_then_damage"
        or lifecycle.get("weather_sensitive_charge_skip") is not True
        or tuple(lifecycle.get("sunny_weather_skip_sources", ())) != ("sunnyday", "desolateland")
        or lifecycle.get("weak_weather_damage_modifier_present") is not True
    ):
        return _result("rejected", "solar_weather_canonical_lifecycle_invalid")

    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    field = state.get("field") if isinstance(state, Mapping) and isinstance(state.get("field"), Mapping) else None
    native = _native_field_state(state) if isinstance(state, Mapping) else {"weather": "unknown"}
    weather = native.get("weather")
    provenance = field.get("weather_provenance") if isinstance(field, Mapping) else None
    if weather == "unknown":
        return {
            **_base(strategy_d0, actor, target, action, lifecycle, metadata),
            "status": "incomplete",
            "schema_version": SCHEMA_VERSION,
            "reason": "solar_current_weather_unknown",
            "weather": {"status": "unknown"},
        }
    if (
        not isinstance(weather, str)
        or not isinstance(provenance, Mapping)
        or provenance.get("event_kind") != "current_weather_observed"
        or provenance.get("trust") != "user_confirmed_observation"
    ):
        return _result("rejected", "solar_current_weather_provenance_invalid")

    outcome = (
        "sunny_skip" if weather in _SUN
        else "weak_weather_charge" if weather in _WEAK
        else "ordinary_charge"
    )
    source_class = (
        ("sunnyday", "desolateland") if weather == "sun"
        else ("raindance", "primordialsea") if weather == "rain"
        else ("sandstorm",) if weather == "sandstorm"
        else ("hail", "snowscape") if weather == "snow"
        else ()
    )
    return {
        **_base(strategy_d0, actor, target, action, lifecycle, metadata),
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "outcome": outcome,
        "weather": {
            "status": "known",
            "value": weather,
            "canonical_source_class": source_class,
            "source_provenance": deepcopy(dict(provenance)),
        },
        "sunny_skip": outcome == "sunny_skip",
        "weak_weather": outcome == "weak_weather_charge",
        "execution_grant": False,
        "provenance": "strict_runtime_d0_solar_charge_weather_decision_v1",
    }


def validate_runtime_d0_solar_charge_weather_decision_authority(
    *, authority: Any, **kwargs: Any,
) -> str | None:
    expected = freeze_runtime_d0_solar_charge_weather_decision_authority(**kwargs)
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "runtime_d0_solar_charge_weather_decision_authority_mismatch"


def _base(
    d0: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(dict(d0.get("decision_owner", {}))),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action.get("action_id"),
        "move_id": action.get("identity"),
        "canonical_charge_lifecycle_authority": deepcopy(dict(lifecycle)),
        "move_metadata_authority": deepcopy(dict(metadata)),
    }


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
