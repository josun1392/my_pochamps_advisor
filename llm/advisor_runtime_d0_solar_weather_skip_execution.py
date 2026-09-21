"""Strict current-D0 sunny-weather Solar skip caller."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_runtime_d0_life_orb_immediate_authority import (
    freeze_runtime_d0_life_orb_immediate_authority,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import (
    freeze_runtime_d0_standard_charge_terminal_mechanics_authority,
    validate_runtime_d0_standard_charge_terminal_mechanics_authority,
)
from llm.advisor_solar_terminal_weather_damage_modifier import (
    materialize_solar_terminal_weather_damage_modifier_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    CALLER_AUTH_SCHEMA_VERSION,
    WEATHER_CURRENT_TURN_SKIP_MODE,
    execute_standard_charge_terminal_attack,
    materialize_standard_charge_terminal_execution_contract,
)

AUTHORITY_SCHEMA_VERSION = "runtime-d0-solar-weather-skip-execution-authority-v1"
_SOLAR = frozenset({"solar-beam", "solar-blade"})


def freeze_runtime_d0_solar_weather_skip_execution_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
    readiness_authority: Mapping[str, Any] | None = None,
    terminal_mechanics_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected_readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    readiness = expected_readiness if readiness_authority is None else readiness_authority
    if not isinstance(readiness, Mapping) or dict(readiness) != expected_readiness:
        return _result("rejected", "solar_weather_skip_readiness_authority_tampered")
    if (
        readiness.get("status") != "resolved"
        or readiness.get("outcome") != "weather_charge_skip_ready"
        or readiness.get("skip_reason") != "weather_skip"
        or readiness.get("next_semantic_phase") != "current_turn_charge_skip_terminal_execution"
        or readiness.get("solar_weather_decision_authority", {}).get("outcome") != "sunny_skip"
        or readiness.get("solar_weather_decision_authority", {}).get("weather", {}).get("value") != "sun"
        or readiness.get("action_execution_confirmed") is not False
        or readiness.get("immediate_damage_execution_grant") is not False
        or readiness.get("charge_turn_state_materialized") is not False
    ):
        return _result("rejected", "solar_weather_skip_readiness_invalid")

    move_id = readiness.get("move_id")
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    lifecycle = effect.get("lifecycle") if isinstance(effect, Mapping) else None
    if (
        move_id not in _SOLAR
        or effect.get("status") != "resolved"
        or not isinstance(lifecycle, Mapping)
        or lifecycle.get("lifecycle_family") != "weather_sensitive_charge_then_damage"
        or lifecycle.get("weather_sensitive_charge_skip") is not True
    ):
        return _result("rejected", "solar_weather_skip_move_not_supported")

    expected_terminal = freeze_runtime_d0_standard_charge_terminal_mechanics_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata=move_metadata,
    )
    terminal = expected_terminal if terminal_mechanics_authority is None else terminal_mechanics_authority
    if terminal_mechanics_authority is not None:
        replay = validate_runtime_d0_standard_charge_terminal_mechanics_authority(
            authority=terminal,
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            action=action,
            actor=actor,
            target=target,
            move_metadata=move_metadata,
        )
        if replay.get("status") != "resolved":
            return _result("rejected", "solar_weather_terminal_mechanics_authority_tampered")
    if not isinstance(terminal, Mapping) or dict(terminal) != expected_terminal:
        return _result("rejected", "solar_weather_terminal_mechanics_authority_tampered")
    if terminal.get("status") != "resolved":
        return _result("incomplete", terminal.get("reason", "solar_weather_terminal_mechanics_incomplete"))

    binding = {
        "session_id": strategy_d0.get("session_id"),
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"),
        "decision_owner": deepcopy(dict(strategy_d0.get("decision_owner", {}))),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action.get("action_id"),
        "move_id": move_id,
    }
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "action_id", "move_id"):
        if readiness.get(key) != binding[key] or terminal.get(key) != binding[key]:
            return _result("rejected", "solar_weather_skip_binding_mismatch")
    if readiness.get("source_target_owner") != binding["target"] or terminal.get("target") != binding["target"]:
        return _result("rejected", "solar_weather_skip_target_binding_mismatch")

    life_orb = freeze_runtime_d0_life_orb_immediate_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        attacker=actor,
        target=target,
        source_action=action,
        move_metadata=effect["move"],
        qualifying_damage=True,
    )
    if life_orb.get("status") != "resolved":
        return _result("incomplete", life_orb.get("reason", "solar_weather_life_orb_authority_unavailable"))

    return {
        "status": "resolved",
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        **binding,
        "canonical_terminal_effect": deepcopy(dict(effect)),
        "move_metadata": deepcopy(dict(effect["move"])),
        "readiness_authority": deepcopy(dict(readiness)),
        "weather_decision_authority": deepcopy(dict(readiness["solar_weather_decision_authority"])),
        "terminal_mechanics_authority": deepcopy(dict(terminal)),
        "attacker_life_orb_terminal_authority": deepcopy(dict(life_orb)),
        "execution_mode": WEATHER_CURRENT_TURN_SKIP_MODE,
        "execution_grant": "authenticated_solar_weather_current_turn_skip_only",
        "provenance": "runtime_d0_solar_weather_skip_execution_authority_v1",
    }


def materialize_runtime_d0_solar_weather_skip_terminal_execution_contract(
    *, execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    error = _self_consistency_error(execution_authority)
    if error is not None:
        return _result("rejected", error)
    terminal = execution_authority["terminal_mechanics_authority"]
    supports = _kernel_supports(execution_authority)
    if supports.get("status") != "resolved":
        return supports
    actor_mechanics = terminal["actor_participant_mechanics_authority"]
    target_mechanics = terminal["target_participant_mechanics_authority"]
    modifier = materialize_solar_terminal_weather_damage_modifier_authority(
        move_id=execution_authority["move_id"],
        actor=execution_authority["actor"],
        target=execution_authority["target"],
        action_id=execution_authority["action_id"],
        source_state_fingerprint=execution_authority["source_runtime_fingerprint"],
        actor_mechanics=actor_mechanics,
    )
    if not isinstance(modifier, Mapping) or modifier.get("status") != "resolved":
        return _result("incomplete", "solar_weather_terminal_modifier_unavailable")

    auth = {
        "schema_version": CALLER_AUTH_SCHEMA_VERSION,
        "caller_kind": "weather_current_turn_skip",
        "execution_mode": WEATHER_CURRENT_TURN_SKIP_MODE,
        "session_id": execution_authority["session_id"],
        "source_state_fingerprint": execution_authority["source_runtime_fingerprint"],
        "decision_owner": deepcopy(dict(execution_authority["decision_owner"])),
        "actor": deepcopy(dict(execution_authority["actor"])),
        "target": deepcopy(dict(execution_authority["target"])),
        "action_id": execution_authority["action_id"],
        "move_id": execution_authority["move_id"],
        "canonical_terminal_effect": deepcopy(dict(execution_authority["canonical_terminal_effect"])),
        "actor_mechanics": deepcopy(dict(actor_mechanics)),
        "target_mechanics": deepcopy(dict(target_mechanics)),
        "attacker_held_item_effect_authority": deepcopy(dict(supports["attacker_item"])),
        "target_held_item_effect_authority": deepcopy(dict(supports["target_item"])),
        "target_sturdy_authority": deepcopy(dict(supports["sturdy"])),
        "target_focus_sash_authority": deepcopy(dict(supports["focus_sash"])),
        "attacker_life_orb_authority": deepcopy(dict(supports["life_orb"])),
        "caller_action_authority": deepcopy(dict(execution_authority)),
        "power_herb_consumption_authority": None,
        "solar_terminal_weather_damage_modifier_authority": deepcopy(dict(modifier)),
        "source_execution_authority": deepcopy(dict(execution_authority)),
        "provenance": "solar_weather_current_turn_terminal_caller_authentication_v1",
    }
    return materialize_standard_charge_terminal_execution_contract(
        execution_mode=WEATHER_CURRENT_TURN_SKIP_MODE,
        source_state_fingerprint=execution_authority["source_runtime_fingerprint"],
        decision_owner=execution_authority["decision_owner"],
        actor=execution_authority["actor"],
        target=execution_authority["target"],
        action_id=execution_authority["action_id"],
        move_id=execution_authority["move_id"],
        canonical_terminal_effect=execution_authority["canonical_terminal_effect"],
        actor_mechanics=actor_mechanics,
        target_mechanics=target_mechanics,
        attacker_held_item_effect_authority=supports["attacker_item"],
        target_held_item_effect_authority=supports["target_item"],
        target_sturdy_authority=supports["sturdy"],
        target_focus_sash_authority=supports["focus_sash"],
        attacker_life_orb_authority=supports["life_orb"],
        caller_action_authority=execution_authority,
        caller_authentication=auth,
        solar_terminal_weather_damage_modifier_authority=modifier,
    )


def execute_runtime_d0_solar_weather_skip(
    *, execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    contract = materialize_runtime_d0_solar_weather_skip_terminal_execution_contract(
        execution_authority=execution_authority,
    )
    if contract.get("status") != "resolved":
        return contract
    return execute_standard_charge_terminal_attack(execution_contract=contract)


def validate_runtime_d0_solar_weather_skip_execution_authority(
    *, authority: Any, **kwargs: Any,
) -> str | None:
    expected = freeze_runtime_d0_solar_weather_skip_execution_authority(**kwargs)
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "runtime_d0_solar_weather_skip_execution_authority_mismatch"


def _kernel_supports(execution: Mapping[str, Any]) -> dict[str, Any]:
    terminal = execution["terminal_mechanics_authority"]
    attacker_item = _item_adapter(
        terminal["actor_held_item_effect_applicability_authority"],
        execution["actor"],
    )
    target_item = _item_adapter(
        terminal["target_held_item_effect_applicability_authority"],
        execution["target"],
    )
    if attacker_item.get("status") != "resolved" or target_item.get("status") != "resolved":
        return _result("incomplete", "solar_weather_item_support_unavailable")
    sturdy = deepcopy(dict(terminal["target_sturdy_authority"]))
    if sturdy.get("status") not in {"ready", "resolved"}:
        return _result("incomplete", "solar_weather_sturdy_support_unavailable")
    sturdy["source_current_d0_authority"] = deepcopy(dict(terminal["target_sturdy_authority"]))
    sash_source = terminal["target_focus_sash_authority"]
    if sash_source.get("status") not in {"ready", "resolved"}:
        return _result("incomplete", "solar_weather_focus_sash_support_unavailable")
    sash = {
        "status": sash_source["status"],
        "schema_version": "detached-next-turn-focus-sash-survival-authority-v1",
        "session_id": execution["session_id"],
        "source_next_decision_fingerprint": execution["source_runtime_fingerprint"],
        "holder": deepcopy(dict(execution["target"])),
        "attacker": deepcopy(dict(execution["actor"])),
        "continuation_action_id": execution["action_id"],
        "move_id": execution["move_id"],
        "current_hp": sash_source.get("current_hp"),
        "maximum_hp": sash_source.get("maximum_hp"),
        "outcome": sash_source.get("outcome"),
        "focus_sash_available": sash_source.get("focus_sash_available", False),
        "eligible": sash_source.get("eligible", False),
        "reason": sash_source.get("reason"),
        "source_current_d0_authority": deepcopy(dict(sash_source)),
        "provenance": "current_d0_solar_weather_focus_sash_kernel_adapter_v1",
    }
    return {
        "status": "resolved",
        "attacker_item": attacker_item,
        "target_item": target_item,
        "sturdy": sturdy,
        "focus_sash": sash,
        "life_orb": deepcopy(dict(execution["attacker_life_orb_terminal_authority"])),
    }


def _item_adapter(source: Mapping[str, Any], holder: Mapping[str, Any]) -> dict[str, Any]:
    if source.get("status") != "resolved":
        return _result("incomplete", "solar_weather_held_item_effect_unavailable")
    current = source.get("current_item_authority", {})
    if current.get("status") == "known":
        effective = current.get("item_id") if source.get("item_effects_active") is True else None
    elif current.get("status") == "known_absent":
        effective = None
    else:
        return _result("incomplete", "solar_weather_held_item_unknown")
    return {
        "status": "resolved",
        "schema_version": "current-d0-standard-charge-kernel-item-adapter-v1",
        "holder": deepcopy(dict(holder)),
        "item_effects_active": source.get("item_effects_active"),
        "effective_item_id": effective,
        "source_current_d0_authority": deepcopy(dict(source)),
        "provenance": "current_d0_solar_weather_item_kernel_adapter_v1",
    }


def _self_consistency_error(value: Any) -> str | None:
    move_id = value.get("move_id") if isinstance(value, Mapping) else None
    if (
        not isinstance(value, Mapping)
        or value.get("status") != "resolved"
        or value.get("schema_version") != AUTHORITY_SCHEMA_VERSION
        or value.get("execution_mode") != WEATHER_CURRENT_TURN_SKIP_MODE
        or not isinstance(move_id, str)
        or move_id not in _SOLAR
    ):
        return "solar_weather_skip_execution_authority_invalid"
    readiness = value.get("readiness_authority")
    terminal = value.get("terminal_mechanics_authority")
    weather = value.get("weather_decision_authority")
    if (
        not isinstance(readiness, Mapping)
        or readiness.get("outcome") != "weather_charge_skip_ready"
        or readiness.get("skip_reason") != "weather_skip"
        or not isinstance(weather, Mapping)
        or weather != readiness.get("solar_weather_decision_authority")
        or weather.get("outcome") != "sunny_skip"
        or weather.get("weather", {}).get("value") != "sun"
        or not isinstance(terminal, Mapping)
        or terminal.get("status") != "resolved"
        or terminal.get("canonical_terminal_effect") != value.get("canonical_terminal_effect")
        or value.get("canonical_terminal_effect") != resolve_canonical_standard_charge_turn_two_effect(value.get("move_id"))
        or not isinstance(value.get("attacker_life_orb_terminal_authority"), Mapping)
        or value["attacker_life_orb_terminal_authority"].get("status") != "resolved"
    ):
        return "solar_weather_skip_execution_authority_tampered"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "action_id", "move_id")
    if any(readiness.get(key) != value.get(key) or terminal.get(key) != value.get(key) for key in keys):
        return "solar_weather_skip_execution_authority_binding_mismatch"
    if readiness.get("source_target_owner") != value.get("target") or terminal.get("target") != value.get("target"):
        return "solar_weather_skip_execution_authority_binding_mismatch"
    return None


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": AUTHORITY_SCHEMA_VERSION, "reason": reason}
