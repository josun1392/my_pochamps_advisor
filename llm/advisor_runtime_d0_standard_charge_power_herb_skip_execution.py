"""Strict current-D0 Power Herb caller for ordinary standard-charge moves.

This owner authenticates the current action and adapts already-frozen D0 facts
to the lifecycle-neutral shared terminal kernel.  It never mutates runtime
state and never fabricates a turn-two continuation.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_standard_charge_turn_two_effects import (
    resolve_canonical_standard_charge_turn_two_effect,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import (
    freeze_runtime_d0_standard_charge_terminal_mechanics_authority,
    validate_runtime_d0_standard_charge_terminal_mechanics_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    CALLER_AUTH_SCHEMA_VERSION,
    POWER_HERB_CURRENT_TURN_SKIP_MODE,
    execute_standard_charge_terminal_attack,
    materialize_standard_charge_terminal_execution_contract,
)
from llm.advisor_solar_terminal_weather_damage_modifier import (
    materialize_solar_terminal_weather_damage_modifier_authority,
)
from llm.advisor_standard_charge_turn_self_stage_effect import (
    freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority,
)

AUTHORITY_SCHEMA_VERSION = "runtime-d0-standard-charge-power-herb-skip-execution-authority-v1"
CONSUMPTION_SCHEMA_VERSION = "detached-standard-charge-power-herb-consumption-authority-v1"
_SUPPORTED = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade", "meteor-beam", "skull-bash", "fly", "dig", "dive", "bounce", "phantom-force", "shadow-force"})
_SOLAR = frozenset({"solar-beam", "solar-blade"})
_SELF_EFFECT = frozenset({"meteor-beam", "skull-bash"})
_SEMI_INVULNERABLE = frozenset({"fly", "dig", "dive", "bounce", "phantom-force", "shadow-force"})


def freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
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
    """Authenticate the exact current-D0 Power Herb skip caller."""
    expected_readiness = freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    readiness = expected_readiness if readiness_authority is None else readiness_authority
    if not isinstance(readiness, Mapping) or dict(readiness) != expected_readiness:
        return _result("rejected", "power_herb_skip_readiness_authority_tampered")
    if readiness.get("status") != "resolved":
        return _result(readiness.get("status", "incomplete"), readiness.get("reason", "power_herb_skip_readiness_unavailable"))
    if (
        readiness.get("outcome") != "power_herb_charge_skip_ready"
        or readiness.get("next_semantic_phase") != "current_turn_charge_skip_terminal_execution"
        or readiness.get("power_herb_applicability_state", {}).get("status") != "active"
        or readiness.get("power_herb_applicability_authority", {}).get("item_effects_active") is not True
        or readiness.get("power_herb_applicability_authority", {}).get("current_item_authority", {}).get("item_id") != "power-herb"
        or readiness.get("current_item_authority", {}).get("item_id") != "power-herb"
        or readiness.get("action_execution_confirmed") is not False
        or readiness.get("immediate_damage_execution_grant") is not False
        or readiness.get("charge_turn_state_materialized") is not False
    ):
        return _result("rejected", "power_herb_skip_readiness_not_active")

    move_id = readiness.get("move_id")
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    lifecycle = effect.get("lifecycle") if isinstance(effect, Mapping) else None
    if (
        move_id not in _SUPPORTED
        or effect.get("status") != "resolved"
        or not isinstance(lifecycle, Mapping)
        or lifecycle.get("lifecycle_family") != (
            "weather_sensitive_charge_then_damage" if move_id in _SOLAR
            else "charge_turn_self_effect_then_damage" if move_id in _SELF_EFFECT
            else "semi_invulnerable_charge_then_damage" if move_id in _SEMI_INVULNERABLE
            else "ordinary_charge_then_damage"
        )
        or lifecycle.get("power_herb_charge_skip_possible") is not True
    ):
        return _result("rejected", "power_herb_skip_move_not_supported")

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
            return _result("rejected", "power_herb_terminal_mechanics_authority_tampered")
    if not isinstance(terminal, Mapping) or dict(terminal) != expected_terminal:
        return _result("rejected", "power_herb_terminal_mechanics_authority_tampered")
    if terminal.get("status") != "resolved":
        return _result("incomplete", terminal.get("reason", "power_herb_terminal_mechanics_incomplete"))
    if terminal.get("mechanics_only") is not True or terminal.get("execution_grant") is not False:
        return _result("rejected", "power_herb_terminal_mechanics_execution_boundary_invalid")

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
    readiness_binding = {**binding, "source_target_owner": binding["target"]}
    if any(readiness.get(key) != value for key, value in readiness_binding.items() if key != "target"):
        return _result("rejected", "power_herb_skip_authority_binding_mismatch")
    if any(terminal.get(key) != value for key, value in binding.items()):
        return _result("rejected", "power_herb_skip_authority_binding_mismatch")

    self_stage = None
    if move_id in _SELF_EFFECT:
        self_stage = freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            action=action,
            actor=actor,
            target=target,
        )
        if self_stage.get("status") != "resolved":
            return _result(
                self_stage.get("status", "incomplete"),
                self_stage.get("reason", "power_herb_charge_turn_self_stage_effect_unavailable"),
            )

    return {
        "status": "resolved",
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        **binding,
        "canonical_terminal_effect": deepcopy(dict(effect)),
        "move_metadata": deepcopy(dict(effect["move"])),
        "readiness_authority": deepcopy(dict(readiness)),
        "held_item_effect_applicability_authority": deepcopy(dict(readiness["power_herb_applicability_authority"])),
        "terminal_mechanics_authority": deepcopy(dict(terminal)),
        **({"charge_turn_self_stage_effect_authority": deepcopy(dict(self_stage))} if isinstance(self_stage, Mapping) else {}),
        "execution_mode": POWER_HERB_CURRENT_TURN_SKIP_MODE,
        "execution_grant": "authenticated_power_herb_current_turn_skip_only",
        "provenance": "runtime_d0_power_herb_standard_charge_skip_execution_authority_v1",
    }


def materialize_detached_standard_charge_power_herb_consumption_authority(
    *, execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the deterministic item transition applied only after gate success."""
    error = _self_consistency_error(execution_authority)
    if error is not None:
        return _result("rejected", error)
    applicability = execution_authority["held_item_effect_applicability_authority"]
    return {
        "status": "resolved",
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "session_id": execution_authority["session_id"],
        "source_runtime_fingerprint": execution_authority["source_runtime_fingerprint"],
        "source_branch_fingerprint": execution_authority["source_branch_fingerprint"],
        "decision_owner": deepcopy(dict(execution_authority["decision_owner"])),
        "actor": deepcopy(dict(execution_authority["actor"])),
        "target": deepcopy(dict(execution_authority["target"])),
        "action_id": execution_authority["action_id"],
        "move_id": execution_authority["move_id"],
        "source_execution_authority": deepcopy(dict(execution_authority)),
        "held_item_effect_applicability_authority": deepcopy(dict(applicability)),
        "item_before": "power-herb",
        "item_after": {"status": "known_absent", "value": None},
        "phase": "after_pre_action_gate_before_accuracy",
        "conditional_on_selected_move_execution": True,
        "hypothetical": True,
        "observation_emitted": False,
        "provenance": "detached_power_herb_conditional_execution_consumption_v1",
    }


def materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract(
    *, execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt current-D0 facts to the shared kernel's exact support contract."""
    error = _self_consistency_error(execution_authority)
    if error is not None:
        return _result("rejected", error)
    terminal = execution_authority["terminal_mechanics_authority"]
    supports = _kernel_supports(execution_authority)
    if supports.get("status") != "resolved":
        return supports
    consumption = materialize_detached_standard_charge_power_herb_consumption_authority(
        execution_authority=execution_authority,
    )
    if consumption.get("status") != "resolved":
        return consumption
    actor_mechanics = terminal["actor_participant_mechanics_authority"]
    target_mechanics = terminal["target_participant_mechanics_authority"]
    solar_modifier = materialize_solar_terminal_weather_damage_modifier_authority(
        move_id=execution_authority["move_id"],
        actor=execution_authority["actor"],
        target=execution_authority["target"],
        action_id=execution_authority["action_id"],
        source_state_fingerprint=execution_authority["source_runtime_fingerprint"],
        actor_mechanics=actor_mechanics,
    )
    if execution_authority["move_id"] in _SOLAR and (
        not isinstance(solar_modifier, Mapping) or solar_modifier.get("status") != "resolved"
    ):
        return _result("incomplete", "power_herb_solar_terminal_weather_modifier_unavailable")

    caller_authentication = {
        "schema_version": CALLER_AUTH_SCHEMA_VERSION,
        "caller_kind": "power_herb_current_turn_skip",
        "execution_mode": POWER_HERB_CURRENT_TURN_SKIP_MODE,
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
        "power_herb_consumption_authority": deepcopy(dict(consumption)),
        **({"solar_terminal_weather_damage_modifier_authority": deepcopy(dict(solar_modifier))} if isinstance(solar_modifier, Mapping) else {}),
        **({"charge_turn_self_stage_effect_authority": deepcopy(dict(execution_authority["charge_turn_self_stage_effect_authority"]))} if isinstance(execution_authority.get("charge_turn_self_stage_effect_authority"), Mapping) else {}),
        "source_execution_authority": deepcopy(dict(execution_authority)),
        "provenance": "power_herb_current_turn_standard_charge_terminal_caller_authentication_v1",
    }
    return materialize_standard_charge_terminal_execution_contract(
        execution_mode=POWER_HERB_CURRENT_TURN_SKIP_MODE,
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
        caller_authentication=caller_authentication,
        power_herb_consumption_authority=consumption,
        solar_terminal_weather_damage_modifier_authority=solar_modifier,
        charge_turn_self_stage_effect_authority=execution_authority.get("charge_turn_self_stage_effect_authority"),
    )


def execute_runtime_d0_standard_charge_power_herb_skip(
    *, execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    contract = materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract(
        execution_authority=execution_authority,
    )
    if contract.get("status") != "resolved":
        return contract
    return execute_standard_charge_terminal_attack(execution_contract=contract)


def validate_runtime_d0_standard_charge_power_herb_skip_execution_authority(
    *, authority: Any, **kwargs: Any,
) -> str | None:
    expected = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(**kwargs)
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "runtime_d0_standard_charge_power_herb_skip_execution_authority_mismatch"


def validate_detached_standard_charge_power_herb_consumption_authority(
    *, authority: Any, execution_authority: Mapping[str, Any],
) -> str | None:
    expected = materialize_detached_standard_charge_power_herb_consumption_authority(
        execution_authority=execution_authority,
    )
    return None if isinstance(authority, Mapping) and deepcopy(dict(authority)) == expected else "detached_standard_charge_power_herb_consumption_authority_mismatch"


def _kernel_supports(execution: Mapping[str, Any]) -> dict[str, Any]:
    terminal = execution["terminal_mechanics_authority"]
    actor_item_source = terminal["actor_held_item_effect_applicability_authority"]
    target_item_source = terminal["target_held_item_effect_applicability_authority"]
    if (
        actor_item_source.get("status") != "resolved"
        or actor_item_source.get("item_effects_active") is not True
        or actor_item_source.get("current_item_authority", {}).get("item_id") != "power-herb"
    ):
        return _result("rejected", "power_herb_attacker_item_support_invalid")
    if target_item_source.get("status") != "resolved":
        return _result("incomplete", "power_herb_target_item_support_unavailable")

    target_current = target_item_source.get("current_item_authority", {})
    if target_current.get("status") == "known":
        target_effective = target_current.get("item_id") if target_item_source.get("item_effects_active") is True else None
    elif target_current.get("status") == "known_absent":
        target_effective = None
    else:
        return _result("incomplete", "power_herb_target_item_unknown")

    attacker_item = {
        "status": "resolved",
        "schema_version": "current-d0-standard-charge-kernel-item-adapter-v1",
        "holder": deepcopy(dict(execution["actor"])),
        "item_effects_active": False,
        "effective_item_id": None,
        "source_current_d0_authority": deepcopy(dict(actor_item_source)),
        "item_transition": "power_herb_consumed_before_accuracy",
        "provenance": "current_d0_power_herb_itemless_attack_boundary_adapter_v1",
    }
    target_item = {
        "status": "resolved",
        "schema_version": "current-d0-standard-charge-kernel-item-adapter-v1",
        "holder": deepcopy(dict(execution["target"])),
        "item_effects_active": target_item_source.get("item_effects_active"),
        "effective_item_id": target_effective,
        "source_current_d0_authority": deepcopy(dict(target_item_source)),
        "provenance": "current_d0_standard_charge_target_item_kernel_adapter_v1",
    }

    sturdy_source = terminal["target_sturdy_authority"]
    if sturdy_source.get("status") not in {"ready", "resolved"}:
        return _result("incomplete", "power_herb_sturdy_support_unavailable")
    sturdy = {
        **deepcopy(dict(sturdy_source)),
        "source_current_d0_authority": deepcopy(dict(sturdy_source)),
        "provenance": "current_d0_standard_charge_sturdy_kernel_adapter_v1",
    }

    sash_source = terminal["target_focus_sash_authority"]
    if sash_source.get("status") not in {"ready", "resolved"}:
        return _result("incomplete", "power_herb_focus_sash_support_unavailable")
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
        "provenance": "current_d0_standard_charge_focus_sash_kernel_adapter_v1",
    }

    life_source = terminal["attacker_life_orb_authority"]
    actor_hp = terminal["actor_participant_mechanics_authority"].get("current_hp", {})
    if (
        life_source.get("status") != "resolved"
        or life_source.get("outcome") != "known_no_effect"
        or life_source.get("attacker_modifier_authorities", {}).get("item_authority", {}).get("value") == "life-orb"
    ):
        return _result("rejected", "power_herb_life_orb_source_not_known_no_effect")
    current_hp, maximum_hp = actor_hp.get("current_hp"), actor_hp.get("maximum_hp")
    if not isinstance(current_hp, int) or not isinstance(maximum_hp, int):
        return _result("incomplete", "power_herb_attacker_hp_unknown")
    life = {
        "status": "resolved",
        "schema_version": "detached-next-turn-life-orb-immediate-authority-v1",
        "session_id": execution["session_id"],
        "source_next_decision_fingerprint": execution["source_runtime_fingerprint"],
        "attacker": deepcopy(dict(execution["actor"])),
        "target": deepcopy(dict(execution["target"])),
        "continuation_action_id": execution["action_id"],
        "move_id": execution["move_id"],
        "qualifying_damage": True,
        "effective_item_id": None,
        "outcome": "known_no_effect",
        "damage_modifier": {"applies": False, "effective_item_id": None},
        "recoil": {
            "eligible": False,
            "damage_fraction": {"numerator": 1, "denominator": 10},
            "rounding": "floor_minimum_one_when_applicable",
            "pre_hp": current_hp,
            "max_hp": maximum_hp,
            "recoil_damage": 0,
            "post_hp": current_hp,
            "fainted": current_hp == 0,
            "suppressed_by": None,
        },
        "source_current_d0_authority": deepcopy(dict(life_source)),
        "provenance": "current_d0_power_herb_itemless_life_orb_kernel_adapter_v1",
    }
    return {
        "status": "resolved",
        "attacker_item": attacker_item,
        "target_item": target_item,
        "sturdy": sturdy,
        "focus_sash": sash,
        "life_orb": life,
    }


def _self_consistency_error(value: Any) -> str | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        return "power_herb_skip_execution_authority_invalid"
    if value.get("execution_mode") != POWER_HERB_CURRENT_TURN_SKIP_MODE:
        return "power_herb_skip_execution_mode_invalid"
    readiness = value.get("readiness_authority")
    terminal = value.get("terminal_mechanics_authority")
    applicability = value.get("held_item_effect_applicability_authority")
    if (
        not isinstance(readiness, Mapping)
        or readiness.get("outcome") != "power_herb_charge_skip_ready"
        or readiness.get("power_herb_applicability_state", {}).get("status") != "active"
        or not isinstance(applicability, Mapping)
        or applicability != readiness.get("power_herb_applicability_authority")
        or applicability.get("item_effects_active") is not True
        or applicability.get("current_item_authority", {}).get("item_id") != "power-herb"
        or not isinstance(terminal, Mapping)
        or terminal.get("status") != "resolved"
        or terminal.get("mechanics_only") is not True
        or terminal.get("execution_grant") is not False
        or value.get("canonical_terminal_effect") != resolve_canonical_standard_charge_turn_two_effect(value.get("move_id"))
    ):
        return "power_herb_skip_execution_authority_tampered"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "action_id", "move_id")
    if any(readiness.get(key) != value.get(key) or terminal.get(key) != value.get(key) for key in keys):
        return "power_herb_skip_execution_authority_binding_mismatch"
    if readiness.get("source_target_owner") != value.get("target") or terminal.get("target") != value.get("target"):
        return "power_herb_skip_execution_authority_binding_mismatch"
    if terminal.get("canonical_terminal_effect") != value.get("canonical_terminal_effect"):
        return "power_herb_skip_terminal_effect_mismatch"
    if value.get("move_id") in _SELF_EFFECT:
        stage = value.get("charge_turn_self_stage_effect_authority")
        if not isinstance(stage, Mapping) or stage.get("move_id") != value.get("move_id") or stage.get("actor") != value.get("actor") or stage.get("target") != value.get("target") or stage.get("action_id") != value.get("action_id"):
            return "power_herb_skip_charge_turn_self_stage_effect_invalid"
    elif value.get("charge_turn_self_stage_effect_authority") is not None:
        return "power_herb_skip_unexpected_charge_turn_self_stage_effect"
    return None


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": AUTHORITY_SCHEMA_VERSION, "reason": reason}
