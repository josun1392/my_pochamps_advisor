"""Strict Geomancy charge/status-terminal execution.

This owner is deliberately status-only.  It consumes authenticated charge
continuation or Power Herb skip callers and never constructs accuracy, critical,
damage-roll, Sturdy, Focus Sash, Life Orb, protection, or targetability
authorities for Geomancy itself.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from advisor.canonical_geomancy_charge_status_terminal import (
    resolve_canonical_geomancy_charge_status_terminal,
)
from llm.advisor_observed_damage_application import apply_canonical_stage_delta
from llm.advisor_runtime_d0_standard_charge_terminal_mechanics_authority import (
    freeze_runtime_d0_standard_charge_participant_mechanics_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    _confusion_self_hit_leaves,
    _pre_action_gate,
)

CONTRACT_SCHEMA_VERSION = "geomancy-charge-status-terminal-contract-v1"
KERNEL_SCHEMA_VERSION = "geomancy-charge-status-terminal-execution-v1"
POWER_HERB_SCHEMA_VERSION = "runtime-d0-geomancy-power-herb-skip-execution-authority-v1"
POWER_HERB_CONSUMPTION_SCHEMA_VERSION = "detached-geomancy-power-herb-consumption-authority-v1"
RETIREMENT_SCHEMA_VERSION = "geomancy-charge-continuation-retirement-v1"
STAGE_SCHEMA_VERSION = "geomancy-terminal-self-stage-transition-v1"
FORCED_MODE = "forced_turn_two_continuation"
POWER_HERB_MODE = "power_herb_current_turn_skip"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STAGE_DELTAS = (("special-attack", 2), ("special-defense", 2), ("speed", 2))


def freeze_runtime_d0_geomancy_power_herb_skip_execution_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
    readiness_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate current-D0 Geomancy Power Herb execution without damage supports."""
    if not _owner(actor) or not _owner(target) or actor == target:
        return _r("rejected", "geomancy_power_herb_identity_invalid")
    if (
        not isinstance(strategy_d0, Mapping)
        or strategy_d0.get("status") != "resolved"
        or strategy_d0.get("decision_owner") != dict(actor)
        or strategy_d0.get("active_owners", {}).get(actor["side"]) != dict(actor)
        or strategy_d0.get("active_owners", {}).get(target["side"]) != dict(target)
        or not isinstance(action, Mapping)
        or action.get("action_type") != "attack"
        or action.get("identity") != "geomancy"
        or not isinstance(action.get("action_id"), str)
        or not isinstance(move_metadata, Mapping)
        or move_metadata.get("move_id") != "geomancy"
    ):
        return _r("rejected", "geomancy_power_herb_binding_invalid")
    canonical = resolve_canonical_geomancy_charge_status_terminal("geomancy")
    if canonical.get("status") != "resolved":
        return _r("rejected", canonical.get("reason", "geomancy_canonical_terminal_unavailable"))
    if (
        not isinstance(readiness_authority, Mapping)
        or readiness_authority.get("status") != "resolved"
        or readiness_authority.get("schema_version") != "runtime-d0-standard-charge-start-readiness-authority-v1"
        or readiness_authority.get("outcome") != "power_herb_charge_skip_ready"
        or readiness_authority.get("move_id") != "geomancy"
        or readiness_authority.get("action_id") != action["action_id"]
        or readiness_authority.get("actor") != dict(actor)
        or readiness_authority.get("source_target_owner") != dict(target)
        or readiness_authority.get("canonical_charge_lifecycle_authority") != canonical["lifecycle"]
        or readiness_authority.get("power_herb_applicability_state", {}).get("status") != "active"
        or readiness_authority.get("current_item_authority", {}).get("status") != "known"
        or readiness_authority.get("current_item_authority", {}).get("item_id") != "power-herb"
        or readiness_authority.get("power_herb_applicability_authority", {}).get("status") != "resolved"
        or readiness_authority.get("power_herb_applicability_authority", {}).get("item_effects_active") is not True
    ):
        return _r("rejected", "geomancy_power_herb_readiness_invalid")
    for key, expected in (
        ("session_id", strategy_d0.get("session_id")),
        ("source_runtime_fingerprint", strategy_d0.get("source_runtime_fingerprint")),
        ("source_branch_fingerprint", strategy_d0.get("strategy_preview_fingerprint")),
        ("decision_owner", strategy_d0.get("decision_owner")),
    ):
        if readiness_authority.get(key) != expected:
            return _r("rejected", "geomancy_power_herb_readiness_binding_mismatch")

    actor_mechanics = freeze_runtime_d0_standard_charge_participant_mechanics_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, owner=actor, participant_role="actor",
        move_metadata=move_metadata,
    )
    target_mechanics = freeze_runtime_d0_standard_charge_participant_mechanics_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=action,
        actor=actor, target=target, owner=target, participant_role="target",
        move_metadata=move_metadata,
    )
    if actor_mechanics.get("status") != "resolved" or target_mechanics.get("status") != "resolved":
        return _r("incomplete", "geomancy_power_herb_participant_mechanics_incomplete")
    return {
        "status": "resolved",
        "schema_version": POWER_HERB_SCHEMA_VERSION,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action["action_id"],
        "move_id": "geomancy",
        "canonical_terminal_effect": canonical,
        "readiness_authority": deepcopy(dict(readiness_authority)),
        "actor_mechanics": deepcopy(dict(actor_mechanics)),
        "target_mechanics": deepcopy(dict(target_mechanics)),
        "damage_terminal_mechanics_authority": None,
        "execution_grant": "authenticated_geomancy_power_herb_skip_only",
        "validation_request": {
            "strategy_d0": deepcopy(dict(strategy_d0)),
            "runtime_snapshot": deepcopy(dict(runtime_snapshot)),
            "action": deepcopy(dict(action)),
            "actor": deepcopy(dict(actor)),
            "target": deepcopy(dict(target)),
            "move_metadata": deepcopy(dict(move_metadata)),
            "readiness_authority": deepcopy(dict(readiness_authority)),
        },
        "provenance": "strict_current_d0_geomancy_power_herb_status_terminal_v1",
    }


def validate_runtime_d0_geomancy_power_herb_skip_execution_authority(
    authority: Any,
) -> str | None:
    if (
        not isinstance(authority, Mapping)
        or authority.get("status") != "resolved"
        or authority.get("schema_version") != POWER_HERB_SCHEMA_VERSION
        or not isinstance(authority.get("validation_request"), Mapping)
    ):
        return "geomancy_power_herb_execution_authority_invalid"
    request = authority["validation_request"]
    required = (
        "strategy_d0", "runtime_snapshot", "action", "actor", "target",
        "move_metadata", "readiness_authority",
    )
    if any(key not in request for key in required):
        return "geomancy_power_herb_execution_validation_request_incomplete"
    expected = freeze_runtime_d0_geomancy_power_herb_skip_execution_authority(
        strategy_d0=request["strategy_d0"],
        runtime_snapshot=request["runtime_snapshot"],
        action=request["action"],
        actor=request["actor"],
        target=request["target"],
        move_metadata=request["move_metadata"],
        readiness_authority=request["readiness_authority"],
    )
    return None if expected == dict(authority) else "geomancy_power_herb_execution_authority_tampered"


def materialize_geomancy_power_herb_consumption_authority(
    execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        validate_runtime_d0_geomancy_power_herb_skip_execution_authority(execution_authority) is not None
        or not isinstance(execution_authority, Mapping)
        or execution_authority.get("status") != "resolved"
        or execution_authority.get("schema_version") != POWER_HERB_SCHEMA_VERSION
        or execution_authority.get("move_id") != "geomancy"
        or execution_authority.get("readiness_authority", {}).get("current_item_authority", {}).get("item_id") != "power-herb"
        or execution_authority.get("readiness_authority", {}).get("power_herb_applicability_state", {}).get("status") != "active"
    ):
        return _r("rejected", "geomancy_power_herb_consumption_source_invalid")
    return {
        "status": "resolved",
        "schema_version": POWER_HERB_CONSUMPTION_SCHEMA_VERSION,
        "actor": deepcopy(dict(execution_authority["actor"])),
        "action_id": execution_authority["action_id"],
        "move_id": "geomancy",
        "phase": "after_pre_action_gate_at_charge_move_skip",
        "item_before": "power-herb",
        "item_after": {"status": "known_absent", "value": None},
        "source_execution_authority": deepcopy(dict(execution_authority)),
        "provenance": "authenticated_geomancy_charge_move_power_herb_consumption_v1",
    }


def materialize_geomancy_status_terminal_contract(
    *,
    execution_mode: str,
    source_state_fingerprint: str,
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action_id: str,
    actor_mechanics: Mapping[str, Any],
    target_mechanics: Mapping[str, Any],
    caller_action_authority: Mapping[str, Any],
    power_herb_consumption_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if execution_mode not in {FORCED_MODE, POWER_HERB_MODE}:
        return _r("rejected", "geomancy_status_terminal_execution_mode_invalid")
    if (
        not _owner(actor) or not _owner(target) or actor == target
        or not isinstance(source_state_fingerprint, str) or not source_state_fingerprint
        or not isinstance(action_id, str) or not action_id
        or not isinstance(actor_mechanics, Mapping) or actor_mechanics.get("status") != "resolved"
        or actor_mechanics.get("owner") != dict(actor)
        or not isinstance(target_mechanics, Mapping) or target_mechanics.get("status") != "resolved"
        or target_mechanics.get("owner") != dict(target)
        or not isinstance(caller_action_authority, Mapping)
    ):
        return _r("rejected", "geomancy_status_terminal_contract_binding_invalid")
    canonical = resolve_canonical_geomancy_charge_status_terminal("geomancy")
    if canonical.get("status") != "resolved":
        return _r("rejected", "geomancy_status_terminal_canonical_unavailable")
    stages = actor_mechanics.get("current_stages", {}).get("values")
    if not isinstance(stages, Mapping) or any(
        not isinstance(stages.get(stat), int) or isinstance(stages.get(stat), bool) or not -6 <= stages[stat] <= 6
        for stat, _delta in _STAGE_DELTAS
    ):
        return _r("incomplete", "geomancy_current_stage_authority_incomplete")
    if execution_mode == FORCED_MODE:
        if power_herb_consumption_authority is not None:
            return _r("rejected", "geomancy_forced_turn_two_power_herb_forbidden")
        if (
            caller_action_authority.get("status") != "resolved"
            or caller_action_authority.get("move_id") != "geomancy"
            or caller_action_authority.get("actor") != dict(actor)
            or caller_action_authority.get("continuation_action_id") != action_id
            or caller_action_authority.get("execution_grant") != "authenticated_standard_charge_turn_two_only"
            or caller_action_authority.get("original_charge_lifecycle", {}).get("canonical_lifecycle_family") != "charge_then_status_terminal"
            or caller_action_authority.get("original_charge_lifecycle", {}).get("execution_model") != "other_two_turn"
        ):
            return _r("rejected", "geomancy_forced_continuation_authority_invalid")
    else:
        source = caller_action_authority
        if (
            source.get("schema_version") != POWER_HERB_SCHEMA_VERSION
            or source.get("status") != "resolved"
            or source.get("move_id") != "geomancy"
            or source.get("actor") != dict(actor)
            or source.get("action_id") != action_id
            or source.get("source_runtime_fingerprint") != source_state_fingerprint
        ):
            return _r("rejected", "geomancy_power_herb_caller_invalid")
        expected_consumption = materialize_geomancy_power_herb_consumption_authority(source)
        if not isinstance(power_herb_consumption_authority, Mapping) or dict(power_herb_consumption_authority) != expected_consumption:
            return _r("rejected", "geomancy_power_herb_consumption_authority_invalid")
    return {
        "status": "resolved",
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "execution_mode": execution_mode,
        "source_state_fingerprint": source_state_fingerprint,
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action_id,
        "move_id": "geomancy",
        "canonical_terminal_effect": canonical,
        "actor_mechanics": deepcopy(dict(actor_mechanics)),
        "target_mechanics": deepcopy(dict(target_mechanics)),
        "caller_action_authority": deepcopy(dict(caller_action_authority)),
        "power_herb_consumption_authority": deepcopy(dict(power_herb_consumption_authority)) if isinstance(power_herb_consumption_authority, Mapping) else None,
        "damage_terminal_mechanics_authority": None,
        "protection_authority": None,
        "semi_invulnerable_state_authority": None,
        "provenance": "typed_geomancy_charge_status_terminal_contract_v1",
    }


def execute_runtime_d0_geomancy_power_herb_skip(
    execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    validation_error = validate_runtime_d0_geomancy_power_herb_skip_execution_authority(execution_authority)
    if validation_error is not None:
        return _r("rejected", validation_error)
    consumption = materialize_geomancy_power_herb_consumption_authority(execution_authority)
    if consumption.get("status") != "resolved":
        return consumption
    contract = materialize_geomancy_status_terminal_contract(
        execution_mode=POWER_HERB_MODE,
        source_state_fingerprint=execution_authority["source_runtime_fingerprint"],
        actor=execution_authority["actor"],
        target=execution_authority["target"],
        action_id=execution_authority["action_id"],
        actor_mechanics=execution_authority["actor_mechanics"],
        target_mechanics=execution_authority["target_mechanics"],
        caller_action_authority=execution_authority,
        power_herb_consumption_authority=consumption,
    )
    return execute_geomancy_status_terminal(contract)


def execute_geomancy_status_terminal(contract: Mapping[str, Any]) -> dict[str, Any]:
    error = _contract_error(contract)
    if error is not None:
        return _r("rejected", error)
    actor = contract["actor_mechanics"]
    target = contract["target_mechanics"]
    gate = _pre_action_gate(actor, target, "geomancy")
    if gate.get("status") != "resolved":
        return _r(gate.get("status", "incomplete"), gate.get("reason", "geomancy_pre_action_gate_unavailable"))
    if gate.get("outcome") == "cancelled":
        leaf = _cancelled_leaf(contract, gate["reason"], Fraction(1, 1))
        return _kernel(contract, gate, (leaf,))
    branches = gate.get("branches", ({"kind": "executes", "executes": True, "probability": _fd(Fraction(1, 1))},))
    leaves: list[dict[str, Any]] = []
    for branch in branches:
        probability = _fraction(branch.get("probability"))
        if probability is None:
            return _r("rejected", "geomancy_pre_action_probability_invalid")
        if not branch.get("executes"):
            if str(branch.get("kind", "")).endswith("confusion_self_hit"):
                row = {
                    "actor": contract["actor"],
                    "target": contract["target"],
                    "action_id": contract["action_id"],
                    "move_id": "geomancy",
                    "actor_mechanics": actor,
                    "target_mechanics": target,
                }
                self_hits = _confusion_self_hit_leaves(
                    row, actor, target, branch, contract["caller_action_authority"],
                )
                if self_hits is None:
                    return _r("incomplete", "geomancy_confusion_self_hit_exact_identity_unavailable")
                for leaf in self_hits:
                    leaf = deepcopy(dict(leaf))
                    leaf["consequences"]["geomancy_terminal_execution"] = {
                        "status": "cancelled",
                        "reason": "confusion_self_hit",
                        "boosts_applied": False,
                    }
                    _attach_retirement(contract, leaf, "confusion_self_hit")
                    leaves.append(leaf)
                continue
            leaf = _cancelled_leaf(contract, str(branch.get("kind")), probability)
            _attach_retirement(contract, leaf, _retirement_reason(str(branch.get("kind"))))
            leaves.append(leaf)
            continue
        leaf = _executed_leaf(contract, str(branch.get("kind")), probability)
        if contract["execution_mode"] == FORCED_MODE:
            _attach_retirement(contract, leaf, "terminal_status_executed")
        leaves.append(leaf)
    return _kernel(contract, gate, tuple(leaves))


def materialize_geomancy_terminal_stage_transition(
    *,
    actor: Mapping[str, Any],
    action_id: str,
    actor_mechanics: Mapping[str, Any],
    canonical_terminal_effect: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    canonical = canonical_terminal_effect or resolve_canonical_geomancy_charge_status_terminal("geomancy")
    if (
        not _owner(actor)
        or not isinstance(action_id, str) or not action_id
        or not isinstance(actor_mechanics, Mapping)
        or actor_mechanics.get("status") != "resolved"
        or actor_mechanics.get("owner") != dict(actor)
        or canonical != resolve_canonical_geomancy_charge_status_terminal("geomancy")
    ):
        return _r("rejected", "geomancy_stage_transition_binding_invalid")
    stages = actor_mechanics.get("current_stages", {}).get("values")
    if not isinstance(stages, Mapping):
        return _r("incomplete", "geomancy_stage_transition_current_stages_missing")
    transitions = []
    for stat, delta in _STAGE_DELTAS:
        previous = stages.get(stat)
        if not isinstance(previous, int) or isinstance(previous, bool) or not -6 <= previous <= 6:
            return _r("incomplete", "geomancy_stage_transition_current_stage_invalid")
        resulting = apply_canonical_stage_delta(previous, delta)
        transitions.append({
            "stat": stat,
            "previous_stage": previous,
            "delta": delta,
            "resulting_stage": resulting,
        })
    changed = tuple(row for row in transitions if row["previous_stage"] != row["resulting_stage"])
    outcome = "executed_stage_changes_applied" if changed else "executed_no_change_all_stages_capped"
    return {
        "status": "resolved",
        "schema_version": STAGE_SCHEMA_VERSION,
        "owner": deepcopy(dict(actor)),
        "action_id": action_id,
        "move_id": "geomancy",
        "timing": "terminal_execution",
        "transitions": tuple(deepcopy(transitions)),
        "outcome": outcome,
        "all_stages_capped": not bool(changed),
        "canonical_terminal_effect": deepcopy(dict(canonical)),
        "provenance": "authenticated_geomancy_terminal_self_stage_transition_v1",
    }


def _executed_leaf(contract: Mapping[str, Any], branch_kind: str, probability: Fraction) -> dict[str, Any]:
    actor = contract["actor_mechanics"]
    target = contract["target_mechanics"]
    stage = materialize_geomancy_terminal_stage_transition(
        actor=contract["actor"],
        action_id=contract["action_id"],
        actor_mechanics=actor,
        canonical_terminal_effect=contract["canonical_terminal_effect"],
    )
    if stage.get("status") != "resolved":
        raise ValueError(stage.get("reason", "geomancy_stage_transition_unavailable"))
    transitions = stage["transitions"]
    changed = tuple(row for row in transitions if row["previous_stage"] != row["resulting_stage"])
    outcome = stage["outcome"]
    consequences: dict[str, Any] = {
        "damage": 0,
        "own_final_hp": actor["current_hp"]["current_hp"],
        "target_final_hp": target["current_hp"]["current_hp"],
        "self_fainted": actor["current_hp"]["current_hp"] == 0,
        "target_ko": target["current_hp"]["current_hp"] == 0,
        "secondary": None,
        "geomancy_terminal_self_stage_transition": stage,
        "geomancy_terminal_execution": {
            "status": "executed",
            "boosts_applied": bool(changed),
            "outcome": outcome,
        },
    }
    consumption = contract.get("power_herb_consumption_authority")
    if isinstance(consumption, Mapping):
        consequences["geomancy_power_herb_consumption"] = deepcopy(dict(consumption))
        consequences["actor_item_after"] = {"status": "known_absent", "value": None}
    return {
        "leaf_id": f"{contract['action_id']}:geomancy-terminal:{branch_kind}",
        "candidate_id": contract["action_id"],
        "action_type": "attack",
        "branch_path": ("pre_action", branch_kind, "geomancy_status_terminal"),
        "probability": _fd(probability),
        "hit_state": "not_applicable",
        "critical_state": "not_applicable",
        "damage_roll": "not_applicable",
        "consequences": consequences,
        "provenance": _provenance(contract),
    }


def _cancelled_leaf(contract: Mapping[str, Any], reason: str, probability: Fraction) -> dict[str, Any]:
    actor = contract["actor_mechanics"]
    target = contract["target_mechanics"]
    leaf = {
        "leaf_id": f"{contract['action_id']}:geomancy-cancelled:{reason}",
        "candidate_id": contract["action_id"],
        "action_type": "attack",
        "branch_path": ("pre_action", reason),
        "probability": _fd(probability),
        "hit_state": "not_applicable",
        "critical_state": "not_applicable",
        "damage_roll": "not_applicable",
        "consequences": {
            "damage": 0,
            "own_final_hp": actor["current_hp"]["current_hp"],
            "target_final_hp": target["current_hp"]["current_hp"],
            "self_fainted": actor["current_hp"]["current_hp"] == 0,
            "target_ko": target["current_hp"]["current_hp"] == 0,
            "secondary": None,
            "execution_failure": reason,
            "geomancy_terminal_execution": {
                "status": "cancelled",
                "reason": reason,
                "boosts_applied": False,
            },
        },
        "provenance": _provenance(contract),
    }
    if contract["execution_mode"] == FORCED_MODE:
        _attach_retirement(contract, leaf, _retirement_reason(reason))
    return leaf


def _attach_retirement(contract: Mapping[str, Any], leaf: dict[str, Any], reason: str) -> None:
    if contract["execution_mode"] != FORCED_MODE:
        return
    caller = contract["caller_action_authority"]
    retirement = {
        "status": "resolved",
        "schema_version": RETIREMENT_SCHEMA_VERSION,
        "owner": deepcopy(dict(contract["actor"])),
        "move_id": "geomancy",
        "original_charge_action_id": caller["original_charge_action_id"],
        "continuation_action_id": contract["action_id"],
        "source_continuation_authority": deepcopy(dict(caller)),
        "state_before": "continuation_pending",
        "state_after": "retired",
        "reason": reason,
        "terminal_reapplication_allowed": False,
        "provenance": "authenticated_geomancy_continuation_retirement_v1",
    }
    leaf["consequences"]["geomancy_continuation_retirement"] = retirement


def _kernel(contract: Mapping[str, Any], gate: Mapping[str, Any], leaves: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    total = sum((_fraction(leaf.get("probability")) or Fraction(0, 1) for leaf in leaves), Fraction(0, 1))
    if total != Fraction(1, 1):
        return _r("rejected", "geomancy_terminal_probability_mass_invalid")
    return {
        "status": "resolved",
        "schema_version": KERNEL_SCHEMA_VERSION,
        "execution_contract": deepcopy(dict(contract)),
        "pre_action_gate": deepcopy(dict(gate)),
        "terminal_leaves": tuple(deepcopy(dict(leaf)) for leaf in leaves),
        "terminal_probability_mass": _fd(total),
        "component_manifest": {
            "pre_action_gate": {"status": "resolved"},
            "self_stage_transition": {"status": "conditional_on_execution"},
            "accuracy": {"status": "not_applicable"},
            "critical": {"status": "not_applicable"},
            "move_damage_roll": {"status": "not_applicable"},
            "protection": {"status": "not_applicable"},
            "semi_invulnerability": {"status": "not_applicable"},
        },
        "provenance": "authenticated_geomancy_charge_status_terminal_execution_v1",
    }


def _contract_error(contract: Any) -> str | None:
    if not isinstance(contract, Mapping) or contract.get("status") != "resolved" or contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        return "geomancy_status_terminal_contract_invalid"
    canonical = resolve_canonical_geomancy_charge_status_terminal("geomancy")
    if contract.get("move_id") != "geomancy" or contract.get("canonical_terminal_effect") != canonical:
        return "geomancy_status_terminal_effect_invalid"
    actor, target = contract.get("actor"), contract.get("target")
    if not _owner(actor) or not _owner(target) or actor == target:
        return "geomancy_status_terminal_identity_invalid"
    if contract.get("actor_mechanics", {}).get("owner") != actor or contract.get("target_mechanics", {}).get("owner") != target:
        return "geomancy_status_terminal_mechanics_identity_invalid"
    replay = materialize_geomancy_status_terminal_contract(
        execution_mode=contract["execution_mode"],
        source_state_fingerprint=contract["source_state_fingerprint"],
        actor=actor,
        target=target,
        action_id=contract["action_id"],
        actor_mechanics=contract["actor_mechanics"],
        target_mechanics=contract["target_mechanics"],
        caller_action_authority=contract["caller_action_authority"],
        power_herb_consumption_authority=contract.get("power_herb_consumption_authority"),
    )
    return None if replay == dict(contract) else "geomancy_status_terminal_contract_tampered"


def _provenance(contract: Mapping[str, Any]) -> dict[str, Any]:
    caller = contract["caller_action_authority"]
    return {
        "session_id": contract["actor"]["session_id"],
        "source_runtime_fingerprint": caller.get("source_runtime_fingerprint", contract["source_state_fingerprint"]),
        "source_branch_fingerprint": caller.get("source_branch_fingerprint", contract["source_state_fingerprint"]),
        "decision_owner": deepcopy(caller.get("decision_owner", contract["actor"])),
        "attacker": deepcopy(dict(contract["actor"])),
        "target": deepcopy(dict(contract["target"])),
        "move_id": "geomancy",
        "action_id": contract["action_id"],
        "geomancy_status_terminal_contract": deepcopy(dict(contract)),
    }


def _retirement_reason(reason: str) -> str:
    lower = reason.lower()
    if "paralysis" in lower:
        return "full_paralysis_cancellation"
    if "sleep" in lower:
        return "sleep_cancellation"
    if "freeze" in lower:
        return "freeze_cancellation"
    if "confusion" in lower:
        return "confusion_self_hit"
    if "faint" in lower:
        return "actor_faint_prevents_continuation"
    return "pre_action_execution_opportunity_consumed"


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _fraction(value: Any) -> Fraction | None:
    if (
        not isinstance(value, Mapping)
        or not isinstance(value.get("numerator"), int) or isinstance(value.get("numerator"), bool)
        or not isinstance(value.get("denominator"), int) or isinstance(value.get("denominator"), bool)
        or value["denominator"] <= 0
    ):
        return None
    return Fraction(value["numerator"], value["denominator"])


def _fd(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _r(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": KERNEL_SCHEMA_VERSION, "reason": reason}
