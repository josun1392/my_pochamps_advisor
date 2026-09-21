"""Lifecycle-neutral terminal execution for authenticated standard-charge attacks.

Caller-specific owners authenticate lifecycle/state and materialize support
authorities before creating this contract.  This module never discovers a
next-turn state, pair-local overlay, runtime D0, or Power Herb skip.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from advisor.damage.crit import crit_probability, resolve_crit_stage
from advisor.damage.crit import is_crit_blocked, select_critical_damage_stages
from advisor.damage.formula import DamageContext, calc_damage_rolls
from llm.advisor_solar_terminal_weather_damage_modifier import (
    validate_solar_terminal_weather_damage_modifier_authority,
)
from advisor.damage.field import Field, SideField
from advisor.damage.stats import apply_boosts
from advisor.damage.abilities import get_ability
from advisor.damage.items import get_item
from advisor.probabilistic_target_flinch_effect_capabilities import resolve_probabilistic_target_flinch_effect_capability
from advisor.probabilistic_target_status_effect_capabilities import resolve_probabilistic_target_status_effect_capability
from llm.advisor_champions_sleep_freeze_action_gate import classify_status_move, resolve_gate_branches
from llm.advisor_champions_confusion_action_gate import resolve_confusion_branches
from llm.advisor_detached_next_turn_focus_sash_survival_authority import apply_detached_focus_sash_single_hit


CONTRACT_SCHEMA_VERSION = "standard-charge-terminal-execution-contract-v1"
CALLER_AUTH_SCHEMA_VERSION = "standard-charge-terminal-caller-authentication-v1"
KERNEL_SCHEMA_VERSION = "standard-charge-terminal-attack-kernel-v1"
FORCED_TURN_TWO_EXECUTION_MODE = "forced_turn_two_continuation"
POWER_HERB_CURRENT_TURN_SKIP_MODE = "power_herb_current_turn_skip"
WEATHER_CURRENT_TURN_SKIP_MODE = "weather_current_turn_skip"
_PRODUCTION_EXECUTION_MODES = {FORCED_TURN_TWO_EXECUTION_MODE, POWER_HERB_CURRENT_TURN_SKIP_MODE, WEATHER_CURRENT_TURN_SKIP_MODE}
_SUPPORTED_MOVES = {"sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade"}
_SOLAR_MOVES = {"solar-beam", "solar-blade"}
_OWNER_KEYS = {"session_id", "side", "slot_index", "pokemon_id"}


def standard_charge_terminal_missing_authority(row: Any) -> tuple[str, ...]:
    """Expose shape incompleteness without granting execution."""
    if not isinstance(row, Mapping):
        return ("mechanics_row",)
    return tuple(_required_missing(row))


def validate_standard_charge_terminal_mechanics_shape(*, actor_mechanics: Any, target_mechanics: Any, canonical_terminal_effect: Any) -> str | None:
    """Validate kernel-consumable mechanics without granting execution."""
    if not isinstance(canonical_terminal_effect, Mapping):
        return "standard_charge_terminal_effect_invalid"
    move_id = canonical_terminal_effect.get("move_id")
    if move_id not in _SUPPORTED_MOVES or canonical_terminal_effect != resolve_canonical_standard_charge_turn_two_effect(move_id):
        return "standard_charge_terminal_effect_invalid"
    for label, row in (("actor", actor_mechanics), ("target", target_mechanics)):
        if not isinstance(row, Mapping) or not _owner(row.get("owner")):
            return f"standard_charge_terminal_{label}_mechanics_owner_invalid"
        missing = _required_missing(row)
        if missing:
            return f"standard_charge_terminal_{label}_mechanics_incomplete"
    return None


def materialize_standard_charge_terminal_execution_contract(
    *,
    execution_mode: str,
    source_state_fingerprint: str,
    decision_owner: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action_id: str,
    move_id: str,
    canonical_terminal_effect: Mapping[str, Any],
    actor_mechanics: Mapping[str, Any],
    target_mechanics: Mapping[str, Any],
    attacker_held_item_effect_authority: Mapping[str, Any],
    target_held_item_effect_authority: Mapping[str, Any],
    target_sturdy_authority: Mapping[str, Any],
    target_focus_sash_authority: Mapping[str, Any],
    attacker_life_orb_authority: Mapping[str, Any],
    caller_action_authority: Mapping[str, Any],
    caller_authentication: Mapping[str, Any],
    power_herb_consumption_authority: Mapping[str, Any] | None = None,
    solar_terminal_weather_damage_modifier_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the typed execution boundary for one authenticated caller mode."""
    if execution_mode not in _PRODUCTION_EXECUTION_MODES:
        return _result("rejected", "standard_charge_terminal_execution_mode_not_enabled")
    if not _owner(actor) or not _owner(target) or not _owner(decision_owner) or actor["session_id"] != target["session_id"] or actor["session_id"] != decision_owner["session_id"]:
        return _result("rejected", "standard_charge_terminal_identity_invalid")
    if not isinstance(source_state_fingerprint, str) or not source_state_fingerprint or not isinstance(action_id, str) or not action_id or move_id not in _SUPPORTED_MOVES:
        return _result("rejected", "standard_charge_terminal_binding_invalid")
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    if effect.get("status") != "resolved" or canonical_terminal_effect != effect:
        return _result("rejected", "standard_charge_terminal_effect_invalid")
    shape_error = validate_standard_charge_terminal_mechanics_shape(
        actor_mechanics=actor_mechanics,
        target_mechanics=target_mechanics,
        canonical_terminal_effect=canonical_terminal_effect,
    )
    if shape_error is not None:
        return _result("incomplete", shape_error)
    if actor_mechanics.get("owner") != dict(actor) or target_mechanics.get("owner") != dict(target):
        return _result("rejected", "standard_charge_terminal_mechanics_identity_mismatch")
    supports = (
        attacker_held_item_effect_authority,
        target_held_item_effect_authority,
        target_sturdy_authority,
        target_focus_sash_authority,
        attacker_life_orb_authority,
    )
    if any(not isinstance(value, Mapping) for value in supports):
        return _result("rejected", "standard_charge_terminal_support_authority_invalid")
    contract = {
        "status": "resolved",
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "execution_mode": execution_mode,
        "session_id": actor["session_id"],
        "source_state_fingerprint": source_state_fingerprint,
        "decision_owner": deepcopy(dict(decision_owner)),
        "actor": deepcopy(dict(actor)),
        "target": deepcopy(dict(target)),
        "action_id": action_id,
        "move_id": move_id,
        "canonical_terminal_effect": deepcopy(dict(canonical_terminal_effect)),
        "actor_mechanics": deepcopy(dict(actor_mechanics)),
        "target_mechanics": deepcopy(dict(target_mechanics)),
        "attacker_held_item_effect_authority": deepcopy(dict(attacker_held_item_effect_authority)),
        "target_held_item_effect_authority": deepcopy(dict(target_held_item_effect_authority)),
        "target_sturdy_authority": deepcopy(dict(target_sturdy_authority)),
        "target_focus_sash_authority": deepcopy(dict(target_focus_sash_authority)),
        "attacker_life_orb_authority": deepcopy(dict(attacker_life_orb_authority)),
        "caller_action_authority": deepcopy(dict(caller_action_authority)),
        "caller_authentication": deepcopy(dict(caller_authentication)),
        "power_herb_consumption_authority": deepcopy(dict(power_herb_consumption_authority)) if isinstance(power_herb_consumption_authority, Mapping) else None,
        "provenance": "authenticated_standard_charge_terminal_execution_contract_v1",
    }
    if move_id in _SOLAR_MOVES:
        if not isinstance(solar_terminal_weather_damage_modifier_authority, Mapping):
            return _result("incomplete", "solar_terminal_weather_damage_modifier_authority_required")
        contract["solar_terminal_weather_damage_modifier_authority"] = deepcopy(dict(solar_terminal_weather_damage_modifier_authority))
    elif solar_terminal_weather_damage_modifier_authority is not None:
        return _result("rejected", "non_solar_terminal_weather_damage_modifier_forbidden")
    error = validate_standard_charge_terminal_execution_contract(contract)
    return contract if error is None else _result("rejected", error)


def validate_standard_charge_terminal_execution_contract(contract: Any) -> str | None:
    """Self-consistency validation; caller evidence is duplicated and bound."""
    if not isinstance(contract, Mapping) or contract.get("status") != "resolved" or contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        return "standard_charge_terminal_execution_contract_invalid"
    execution_mode = contract.get("execution_mode")
    if execution_mode not in _PRODUCTION_EXECUTION_MODES:
        return "standard_charge_terminal_execution_mode_invalid"
    consumption = contract.get("power_herb_consumption_authority")
    if execution_mode in {FORCED_TURN_TWO_EXECUTION_MODE, WEATHER_CURRENT_TURN_SKIP_MODE} and consumption is not None:
        return "standard_charge_terminal_consumption_authority_forbidden"
    if execution_mode == POWER_HERB_CURRENT_TURN_SKIP_MODE and not isinstance(consumption, Mapping):
        return "standard_charge_terminal_power_herb_consumption_authority_required"
    actor, target, decision_owner = contract.get("actor"), contract.get("target"), contract.get("decision_owner")
    if not _owner(actor) or not _owner(target) or not _owner(decision_owner):
        return "standard_charge_terminal_contract_owner_invalid"
    session_id = contract.get("session_id")
    if any(owner.get("session_id") != session_id for owner in (actor, target, decision_owner)):
        return "standard_charge_terminal_contract_session_mismatch"
    if not isinstance(contract.get("source_state_fingerprint"), str) or not contract["source_state_fingerprint"]:
        return "standard_charge_terminal_contract_fingerprint_invalid"
    move_id = contract.get("move_id")
    if not isinstance(contract.get("action_id"), str) or not contract["action_id"] or not isinstance(move_id, str) or move_id not in _SUPPORTED_MOVES:
        return "standard_charge_terminal_contract_action_invalid"
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    if contract.get("canonical_terminal_effect") != effect:
        return "standard_charge_terminal_contract_effect_mismatch"
    if contract.get("actor_mechanics", {}).get("owner") != actor or contract.get("target_mechanics", {}).get("owner") != target:
        return "standard_charge_terminal_contract_mechanics_owner_mismatch"
    shape_error = validate_standard_charge_terminal_mechanics_shape(
        actor_mechanics=contract.get("actor_mechanics"),
        target_mechanics=contract.get("target_mechanics"),
        canonical_terminal_effect=contract.get("canonical_terminal_effect"),
    )
    if shape_error is not None:
        return shape_error
    solar_modifier = contract.get("solar_terminal_weather_damage_modifier_authority")
    if move_id in _SOLAR_MOVES:
        if not isinstance(solar_modifier, Mapping):
            return "solar_terminal_weather_damage_modifier_authority_required"
        if validate_solar_terminal_weather_damage_modifier_authority(
            authority=solar_modifier,
            move_id=move_id,
            actor=actor,
            target=target,
            action_id=contract["action_id"],
            source_state_fingerprint=contract["source_state_fingerprint"],
            actor_mechanics=contract["actor_mechanics"],
        ) is not None:
            return "solar_terminal_weather_damage_modifier_authority_invalid"
    elif solar_modifier is not None:
        return "non_solar_terminal_weather_damage_modifier_forbidden"
    auth = contract.get("caller_authentication")
    if not _caller_authentication_matches(contract, auth):
        return "standard_charge_terminal_caller_authentication_mismatch"
    return None


def execute_standard_charge_terminal_attack(*, execution_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Execute D-K terminal mechanics from one authenticated charge contract."""
    error = validate_standard_charge_terminal_execution_contract(execution_contract)
    if error is not None:
        return _result("rejected", error)
    terminal = {
        "status": "resolved",
        "attacker_item": deepcopy(dict(execution_contract["attacker_held_item_effect_authority"])),
        "target_item": deepcopy(dict(execution_contract["target_held_item_effect_authority"])),
        "sturdy": deepcopy(dict(execution_contract["target_sturdy_authority"])),
        "focus_sash": deepcopy(dict(execution_contract["target_focus_sash_authority"])),
        "life_orb": deepcopy(dict(execution_contract["attacker_life_orb_authority"])),
        "solar_weather_modifier": deepcopy(dict(execution_contract["solar_terminal_weather_damage_modifier_authority"])) if isinstance(execution_contract.get("solar_terminal_weather_damage_modifier_authority"), Mapping) else None,
    }
    return _execute_authenticated_terminal_mechanics(
        row=execution_contract,
        actor=execution_contract["actor_mechanics"],
        target=execution_contract["target_mechanics"],
        terminal=terminal,
        caller_action_authority=execution_contract["caller_action_authority"],
        power_herb_consumption_authority=execution_contract.get("power_herb_consumption_authority"),
    )


def execute_authenticated_terminal_mechanics_compatibility(
    *,
    row: Mapping[str, Any],
    actor_mechanics: Mapping[str, Any],
    target_mechanics: Mapping[str, Any],
    terminal_authorities: Mapping[str, Any],
) -> dict[str, Any]:
    """Legacy ordinary-action compatibility over the single D-K mechanics engine.

    This is not a standard-charge execution grant and does not accept a
    mechanics-only current-D0 bundle. Caller-specific code must authenticate
    identity/state and materialize terminal supports before invoking it.
    """
    if not isinstance(row, Mapping) or not isinstance(actor_mechanics, Mapping) or not isinstance(target_mechanics, Mapping):
        return _result("rejected", "terminal_mechanics_compatibility_input_invalid")
    if not isinstance(terminal_authorities, Mapping) or terminal_authorities.get("status") != "resolved":
        return _result("rejected", "terminal_mechanics_compatibility_support_invalid")
    normalized = {
        **deepcopy(dict(row)),
        "action_id": row.get("continuation_action_id", row.get("action_id")),
        "actor_mechanics": deepcopy(dict(actor_mechanics)),
        "target_mechanics": deepcopy(dict(target_mechanics)),
    }
    if not isinstance(normalized.get("action_id"), str) or not normalized["action_id"]:
        return _result("rejected", "terminal_mechanics_compatibility_action_invalid")
    return _execute_authenticated_terminal_mechanics(
        row=normalized,
        actor=actor_mechanics,
        target=target_mechanics,
        terminal=terminal_authorities,
        caller_action_authority=row,
    )


def _execute_authenticated_terminal_mechanics(
    *,
    row: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    terminal: Mapping[str, Any],
    caller_action_authority: Mapping[str, Any],
    power_herb_consumption_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate = _pre_action_gate(actor, target, row["move_id"])
    if gate["status"] == "incomplete":
        return {
            "status": "incomplete", "schema_version": KERNEL_SCHEMA_VERSION,
            "reason": gate["reason"],
            "execution_authority": deepcopy(dict(caller_action_authority)),
            "pre_action_gate": gate,
        }
    if gate["outcome"] == "cancelled":
        return _cancelled(row, gate, caller_action_authority)
    opportunities = gate.get("branches", ({"kind": "executes", "executes": True, "probability": _fd(Fraction(1))},))
    attack_actor = _actor_after_execution_boundary(actor, power_herb_consumption_authority)
    if attack_actor is None:
        return _incomplete(row, "power_herb_consumption_authority_invalid", caller_action_authority)
    actor_stages, target_stages = attack_actor["current_stages"]["values"], target["current_stages"]["values"]
    move = row["canonical_terminal_effect"]["move"]
    accuracy = _accuracy(move["accuracy"], actor_stages["accuracy"], target_stages["evasion"])
    if accuracy is None:
        return _incomplete(row, "detached_accuracy_stage_adapter_unavailable", caller_action_authority)
    crit_stage = resolve_crit_stage(
        {"ability": _value(attack_actor["ability"]), "item": _value(attack_actor["item"]), "types": tuple(attack_actor["types"]["value"]), "volatiles": _volatiles(attack_actor["critical_hit_volatiles"])},
        {"move_id": move["move_id"]},
        {"ability": _value(target["ability"]), "status": _condition(target["condition"])},
    )
    crit = Fraction(0, 1) if is_crit_blocked(
        {"ability": _value(target["ability"])},
        {"lucky_chant": target["lucky_chant"].get("status") == "known_active"},
    ) else crit_probability(crit_stage)
    leaves: list[dict[str, Any]] = []
    for opportunity in opportunities:
        root = _fraction(opportunity["probability"])
        if not opportunity.get("executes"):
            if opportunity.get("kind", "").endswith("confusion_self_hit"):
                self_hits = _confusion_self_hit_leaves(row, actor, target, opportunity, caller_action_authority)
                if self_hits is None:
                    return _incomplete(row, "confusion_self_hit_exact_identity_unavailable", caller_action_authority)
                leaves.extend(self_hits)
                continue
            leaves.append(_gate_cancelled_leaf(row, actor, target, opportunity, caller_action_authority))
            continue
        execution_actor = attack_actor
        if accuracy < 1:
            miss = _miss_leaf(row, execution_actor, target, root * (1 - accuracy), caller_action_authority)
            _attach_power_herb_consumption(miss, power_herb_consumption_authority)
            miss["branch_path"] = ("pre_action", opportunity["kind"], *miss["branch_path"])
            leaves.append(miss)
        for critical, cp in ((False, 1 - crit), (True, crit)):
            if not cp:
                continue
            rolls = _damage_rolls(
                row, critical,
                terminal["attacker_item"]["effective_item_id"],
                terminal["target_item"]["effective_item_id"],
                execution_actor, target,
                terminal.get("solar_weather_modifier"),
            )
            if rolls is None:
                return _incomplete(row, "detached_damage_context_unavailable", caller_action_authority)
            for index, damage in enumerate(rolls):
                event = _hit_event(
                    row, execution_actor, target, critical, index, damage,
                    root * accuracy * cp * Fraction(1, 16), terminal,
                    caller_action_authority,
                )
                _attach_power_herb_consumption(event, power_herb_consumption_authority)
                event["branch_path"] = ("pre_action", opportunity["kind"], *event["branch_path"])
                secondary = _secondary_branches(row, execution_actor, target, event)
                if isinstance(secondary, Mapping):
                    return _incomplete(
                        row,
                        secondary.get("reason", "detached_secondary_capability_unavailable"),
                        caller_action_authority,
                    )
                if secondary is None:
                    return _incomplete(row, "detached_secondary_capability_unavailable", caller_action_authority)
                leaves.extend(_apply_life_orb(secondary, terminal["life_orb"], damage > 0))
    total = sum((_fraction(leaf["probability"]) for leaf in leaves), Fraction())
    if total != 1:
        return _incomplete(row, "detached_attack_ledger_probability_not_normalized", caller_action_authority)
    return {
        "status": "resolved",
        "schema_version": KERNEL_SCHEMA_VERSION,
        "execution_authority": deepcopy(dict(caller_action_authority)),
        "terminal_authorities": deepcopy(dict(terminal)),
        "pre_action_gate": gate,
        "hit_probability": _fd(accuracy),
        "critical_probability": _fd(crit),
        "terminal_leaves": tuple(leaves),
        "terminal_probability_mass": _fd(total),
        "component_manifest": {
            "accuracy": {"status": "resolved"},
            "critical": {"status": "resolved", "stage": crit_stage},
            "damage_roll": {"status": "resolved", "roll_count_per_critical_context": 16},
            "secondary": {"status": "resolved"},
        },
        "provenance": "authenticated_standard_charge_shared_terminal_attack_kernel_v1",
    }


def _caller_authentication_matches(contract: Mapping[str, Any], auth: Any) -> bool:
    if not isinstance(auth, Mapping) or auth.get("schema_version") != CALLER_AUTH_SCHEMA_VERSION:
        return False
    expected_keys = [
        "execution_mode", "session_id", "source_state_fingerprint", "decision_owner",
        "actor", "target", "action_id", "move_id", "canonical_terminal_effect",
        "actor_mechanics", "target_mechanics", "attacker_held_item_effect_authority",
        "target_held_item_effect_authority", "target_sturdy_authority",
        "target_focus_sash_authority", "attacker_life_orb_authority",
        "caller_action_authority", "power_herb_consumption_authority",
    ]
    if contract.get("move_id") in _SOLAR_MOVES:
        expected_keys.append("solar_terminal_weather_damage_modifier_authority")
    if any(auth.get(key) != contract.get(key) for key in expected_keys):
        return False
    source = auth.get("source_execution_authority")
    caller = contract.get("caller_action_authority")
    mode = contract.get("execution_mode")
    if mode == FORCED_TURN_TWO_EXECUTION_MODE:
        side = contract.get("actor", {}).get("side")
        return (
            auth.get("caller_kind") == "forced_turn_two_continuation"
            and isinstance(source, Mapping)
            and source.get("schema_version") == "detached-standard-charge-turn-two-execution-authority-v1"
            and source.get("source_next_decision_fingerprint") == contract.get("source_state_fingerprint")
            and isinstance(source.get("actions"), Mapping)
            and source["actions"].get(side) == caller
            and contract.get("power_herb_consumption_authority") is None
            and auth.get("provenance") == "forced_turn_two_standard_charge_terminal_caller_authentication_v1"
        )
    if mode == WEATHER_CURRENT_TURN_SKIP_MODE:
        return (
            auth.get("caller_kind") == "weather_current_turn_skip"
            and isinstance(source, Mapping)
            and source.get("schema_version") == "runtime-d0-solar-weather-skip-execution-authority-v1"
            and source.get("source_runtime_fingerprint") == contract.get("source_state_fingerprint")
            and source == caller
            and contract.get("power_herb_consumption_authority") is None
            and auth.get("provenance") == "solar_weather_current_turn_terminal_caller_authentication_v1"
        )
    consumption = contract.get("power_herb_consumption_authority")
    return (
        mode == POWER_HERB_CURRENT_TURN_SKIP_MODE
        and auth.get("caller_kind") == "power_herb_current_turn_skip"
        and isinstance(source, Mapping)
        and source.get("schema_version") == "runtime-d0-standard-charge-power-herb-skip-execution-authority-v1"
        and source.get("source_runtime_fingerprint") == contract.get("source_state_fingerprint")
        and source == caller
        and isinstance(consumption, Mapping)
        and consumption.get("schema_version") == "detached-standard-charge-power-herb-consumption-authority-v1"
        and consumption.get("source_execution_authority") == source
        and consumption.get("phase") == "after_pre_action_gate_before_accuracy"
        and consumption.get("item_before") == "power-herb"
        and consumption.get("item_after") == {"status": "known_absent", "value": None}
        and auth.get("provenance") == "power_herb_current_turn_standard_charge_terminal_caller_authentication_v1"
    )


def _actor_after_execution_boundary(actor: Mapping[str, Any], consumption: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if consumption is None:
        return deepcopy(dict(actor))
    if (
        consumption.get("schema_version") != "detached-standard-charge-power-herb-consumption-authority-v1"
        or consumption.get("status") != "resolved"
        or consumption.get("phase") != "after_pre_action_gate_before_accuracy"
        or consumption.get("item_before") != "power-herb"
        or consumption.get("item_after") != {"status": "known_absent", "value": None}
    ):
        return None
    result = deepcopy(dict(actor))
    result["item"] = {"status": "known_absent", "value": None}
    direct = result.get("direct_mechanics")
    combatant = direct.get("combatant") if isinstance(direct, Mapping) else None
    if isinstance(combatant, Mapping):
        direct = deepcopy(dict(direct))
        direct["combatant"] = {**deepcopy(dict(combatant)), "item": None}
        result["direct_mechanics"] = direct
    return result


def _attach_power_herb_consumption(leaf: dict[str, Any], consumption: Mapping[str, Any] | None) -> None:
    if consumption is None:
        return
    consequences = leaf.setdefault("consequences", {})
    consequences["power_herb_consumption"] = deepcopy(dict(consumption))
    consequences["actor_item_after"] = {"status": "known_absent", "value": None}
    consequences["hypothetical_self_item"] = {
        "status": "known_absent", "value": None,
        "source": "exact_terminal_leaf_power_herb_consumption",
        "effect": deepcopy(dict(consumption)),
    }


def _required_missing(row: Mapping[str, Any]) -> list[str]:
    required = (
        "current_level", "current_final_stats", "current_hp", "current_stages",
        "condition", "item", "ability", "types", "substitute",
        "critical_hit_volatiles", "lucky_chant", "field", "side_conditions",
        "direct_mechanics",
    )
    return [
        key for key in required
        if not isinstance(row.get(key), Mapping)
        or row[key].get("status") not in {
            "known", "known_none", "known_present", "known_absent",
            "known_active", "known_inactive",
        }
    ]


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _OWNER_KEYS
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": CONTRACT_SCHEMA_VERSION, "reason": reason}


def _apply_life_orb(leaves: list[dict[str, Any]], authority: Mapping[str, Any], qualifying_damage: bool) -> list[dict[str, Any]]:
    if not qualifying_damage:
        return leaves
    recoil = authority.get("recoil", {})
    if not isinstance(recoil, Mapping): return leaves
    out=[]
    for leaf in leaves:
        updated=deepcopy(leaf); consequence=updated["consequences"]
        consequence["life_orb"] = deepcopy(dict(authority))
        consequence["own_final_hp"] = recoil.get("post_hp", consequence.get("own_final_hp"))
        consequence["self_fainted"] = recoil.get("fainted", consequence.get("self_fainted"))
        out.append(updated)
    return out



def _damage_rolls(row: Mapping[str, Any], critical: bool, attacker_item: str | None, defender_item: str | None, actor: Mapping[str, Any] | None = None, target: Mapping[str, Any] | None = None, solar_weather_modifier: Mapping[str, Any] | None = None) -> list[int] | None:
    a, t, move = actor or row["actor_mechanics"], target or row["target_mechanics"], row["canonical_terminal_effect"]["move"]
    av, tv = a["current_final_stats"]["values"], t["current_final_stats"]["values"]
    ast, tst = a["current_stages"]["values"], t["current_stages"]["values"]
    offense, defense = ("attack", "defense") if move["category"] == "physical" else ("special-attack", "special-defense")
    os, ds = select_critical_damage_stages(ast[offense], tst[defense], is_critical=critical)
    try:
        field = _field(a["field"], t["side_conditions"])
        weather_mod_q12 = solar_weather_modifier.get("modifier_q12") if isinstance(solar_weather_modifier, Mapping) else 4096
        if not isinstance(weather_mod_q12, int):
            return None
        ctx = DamageContext(attacker_level=a["current_level"]["value"], move_power=move["power"], attack_stat=apply_boosts(av[offense], os), defense_stat=apply_boosts(tv[defense], ds), move_type=move["type"], move_id=move["move_id"], attacker_types=tuple(a["types"]["value"]), defender_types=tuple(t["types"]["value"]), is_physical=move["category"] == "physical", is_critical=critical, is_spread=False, field=field, weather_mod_q12=weather_mod_q12, attacker_ability=get_ability(_value(a["ability"])), defender_ability=get_ability(_value(t["ability"])), attacker_item=get_item(attacker_item), defender_item=get_item(defender_item), attacker_hp_current=a["current_hp"]["current_hp"], attacker_hp_max=a["current_hp"]["maximum_hp"], defender_hp_current=t["current_hp"]["current_hp"], defender_hp_max=t["current_hp"]["maximum_hp"], attacker_condition=_condition(a["condition"]) or "none")
        return calc_damage_rolls(ctx)
    except (KeyError, TypeError, ValueError):
        return None


def _hit_event(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], critical: bool, index: int, damage: int, probability: Fraction, terminal: Mapping[str, Any], caller_action_authority: Mapping[str, Any]) -> dict[str, Any]:
    hp = target["current_hp"]["current_hp"]; actual = min(hp, damage); post = hp - actual
    consequence = {"damage": actual, "raw_damage": damage, "own_final_hp": actor["current_hp"]["current_hp"], "target_final_hp": post, "target_ko": post == 0, "self_fainted": False, "secondary": None, "sturdy_survival": {"outcome": "not_activated"}, "focus_sash_survival": {"outcome": "not_activated"}}
    if post == 0 and terminal["sturdy"].get("status") == "ready":
        consequence.update({"target_final_hp": 1, "target_ko": False, "sturdy_survival": {"outcome": "activated", "authority": deepcopy(terminal["sturdy"]), "final_hp": 1}})
    elif post == 0:
        sash = apply_detached_focus_sash_single_hit(authority=terminal["focus_sash"], damage=damage, source_action_id=row["action_id"], source_hit_id=f"roll:{index}")
        if sash.get("status") != "resolved":
            consequence["focus_sash_survival"] = sash
        elif sash.get("outcome") == "activated":
            consequence.update({"target_final_hp": 1, "target_ko": False, "focus_sash_survival": sash, "target_item_after": deepcopy(sash["item_after"])})
    return {"leaf_id": f"{row['action_id']}:hit:{'critical' if critical else 'noncritical'}:roll:{index}", "candidate_id": row["action_id"], "action_type": "attack", "branch_path": ("hit", "critical" if critical else "noncritical", f"damage_roll:{index}"), "probability": _fd(probability), "hit_state": "hit", "critical_state": "critical" if critical else "non_critical", "damage_roll": {"roll_index": index, "random_factor_percent": 85 + index}, "consequences": consequence, "provenance": _leaf_provenance(row, caller_action_authority)}


def _miss_leaf(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], probability: Fraction, caller_action_authority: Mapping[str, Any]) -> dict[str, Any]:
    return {"leaf_id": f"{row['action_id']}:miss", "candidate_id": row["action_id"], "action_type": "attack", "branch_path": ("miss",), "probability": _fd(probability), "hit_state": "miss", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "own_final_hp": actor["current_hp"]["current_hp"], "target_final_hp": target["current_hp"]["current_hp"], "target_ko": False, "self_fainted": False, "secondary": None, "sturdy_survival": {"outcome": "not_activated"}, "focus_sash_survival": {"outcome": "not_activated"}, "life_orb": {"outcome": "not_triggered"}}, "provenance": _leaf_provenance(row, caller_action_authority)}


def _secondary_branches(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], event: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    secondary = row["canonical_terminal_effect"]["secondary"]
    if secondary["kind"] == "none":
        return [deepcopy(dict(event))]
    # A KO and Substitute are terminal eligibility gates, before catalog modifiers.
    if event["consequences"]["target_ko"] or target["substitute"].get("status") == "known_active":
        return [deepcopy(dict(event))]
    source = _secondary_source(actor, target)
    if secondary["kind"] == "flinch":
        cap = resolve_probabilistic_target_flinch_effect_capability(move=row["canonical_terminal_effect"]["move"], source_authority=source)
    else:
        cap = resolve_probabilistic_target_status_effect_capability(move=row["canonical_terminal_effect"]["move"], source_authority=source)
    if cap.get("status") != "resolved":
        return {
            "status": cap.get("status", "incomplete"),
            "reason": cap.get("reason", "detached_secondary_capability_unavailable"),
            "capability_resolution": deepcopy(dict(cap)),
        }
    chance = _fraction(cap["probability"])
    no = deepcopy(dict(event)); no["leaf_id"] += ":secondary:none"; no["branch_path"] += ("secondary:none",); no["probability"] = _fd(_fraction(event["probability"]) * (1 - chance))
    yes = deepcopy(dict(event)); yes["leaf_id"] += f":secondary:{secondary.get('condition', 'flinch')}"; yes["branch_path"] += (f"secondary:{secondary.get('condition', 'flinch')}",); yes["probability"] = _fd(_fraction(event["probability"]) * chance)
    if secondary["kind"] == "flinch":
        yes["consequences"]["secondary"] = {"branch": "effect", "state": "flinched", "hypothetical_target_flinch": {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "provenance": "standard_charge_successful_damage_roll_secondary_v1"}, "authority": cap}
    else:
        yes["consequences"]["secondary"] = {
            "branch": "effect",
            "state": "status_applied",
            "condition": secondary["condition"],
            "hypothetical_target_condition": {
                "schema_version": "detached-hypothetical-current-condition-v1",
                "resulting_condition": secondary["condition"],
                "source_move_id": row["move_id"],
                "provenance": "standard_charge_successful_damage_roll_target_status_secondary_v1",
            },
            "authority": cap,
            "provenance": "standard_charge_successful_damage_roll_target_status_secondary_v1",
        }
    return [no, yes]


def _secondary_source(actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    terrain = actor["field"]
    exact_groundedness = target.get("groundedness")
    if isinstance(exact_groundedness, Mapping) and exact_groundedness.get("status") == "known" and exact_groundedness.get("value") in {"grounded", "ungrounded"}:
        groundedness = deepcopy(dict(exact_groundedness))
    else:
        direct = target["direct_mechanics"].get("combatant", {})
        grounded = direct.get("grounded")
        groundedness = (
            {"status": "known", "value": "grounded"}
            if grounded is True else {"status": "known", "value": "ungrounded"}
            if grounded is False else {"status": "unknown"}
        )
    target_item = target["item"]
    item_source = (
        {"status": "known_absent"}
        if isinstance(target_item, Mapping) and target_item.get("status") == "known_absent"
        else {"status": "known", "value": target_item.get("value")}
        if isinstance(target_item, Mapping) and target_item.get("status") == "known" and isinstance(target_item.get("value"), str)
        else {"status": "unknown"}
    )
    target_condition = target["condition"]
    condition_source = (
        {"status": "known_none"}
        if isinstance(target_condition, Mapping) and target_condition.get("status") == "known_none"
        else {"status": "known_present", "condition": target_condition.get("condition")}
        if isinstance(target_condition, Mapping) and target_condition.get("status") == "known_present" and isinstance(target_condition.get("condition"), str)
        else {"status": "unknown"}
    )
    return {"target_condition": condition_source, "target_types": {"status": "known", "values": tuple(target["types"]["value"])}, "attacker_ability": deepcopy(actor["ability"]), "target_ability": deepcopy(target["ability"]), "target_item": item_source, "terrain": {"status": "known", "value": terrain.get("terrain", "none")}, "target_groundedness": groundedness}


def _pre_action_gate(actor: Mapping[str, Any], target: Mapping[str, Any], move_id: str) -> dict[str, Any]:
    if actor.get("fainted") is True or actor["current_hp"].get("current_hp") == 0:
        return {"status": "resolved", "outcome": "cancelled", "reason": "fainted_actor"}
    condition = actor["condition"]
    current = _condition(condition) or "none"
    if current == "paralysis":
        status = [{"kind": "cancelled_due_to_paralysis", "executes": False, "probability": _fd(Fraction(1, 8))}, {"kind": "executes_after_paralysis", "executes": True, "probability": _fd(Fraction(7, 8))}]
    elif current in {"sleep", "freeze"}:
        progression = actor.get("status_progression", {})
        if not isinstance(progression, Mapping) or progression.get("status") != "known": return {"status": "incomplete", "reason": "champions_status_progression_missing"}
        ability = _gate_ability(actor, target)
        branches = resolve_gate_branches(condition=current, progression=progression.get("value"), ability=ability, move_authority=classify_status_move(move_id))
        if isinstance(branches, Mapping): return dict(branches)
        status = branches
    else:
        status = [{"kind": "executes", "executes": True, "probability": _fd(Fraction(1))}]
    # Confusion is consumed only by a status-executable opportunity.
    confusion = actor.get("confusion_state")
    if not isinstance(confusion, Mapping) or confusion.get("status") == "unknown": return {"status": "incomplete", "reason": "champions_confusion_current_state_unknown"}
    result=[]
    for branch in status:
        if not branch.get("executes"): result.append(branch); continue
        if confusion.get("status") == "known_none": result.append(branch); continue
        progression = actor.get("confusion_progression", {})
        if confusion.get("status") != "known_confused" or not isinstance(progression, Mapping) or progression.get("status") != "known": return {"status": "incomplete", "reason": "champions_confusion_progression_missing_or_stale"}
        rows = resolve_confusion_branches(progression=progression.get("value"), ability=_confusion_ability(actor, target))
        if isinstance(rows, Mapping): return dict(rows)
        for c in rows: result.append({**c, "kind": f"{branch['kind']}:{c['kind']}", "probability": _fd(_fraction(branch["probability"]) * _fraction(c["probability"]))})
    return {"status": "resolved", "outcome": "branches", "branches": tuple(result)}


def _gate_ability(actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    abilities = {"self": _value(actor["ability"]) if actor["owner"]["side"] == "self" else _value(target["ability"]), "opponent": _value(actor["ability"]) if actor["owner"]["side"] == "opponent" else _value(target["ability"])}
    exact = all(isinstance(value, str) and value for value in abilities.values()); own = abilities[actor["owner"]["side"]]; gas = "neutralizing-gas" in abilities.values()
    return {"status": "resolved" if exact else "incomplete", "abilities": abilities, "ability_id": own, "suppressed": gas, "early_bird_active": exact and own == "early-bird" and not gas}


def _confusion_ability(actor: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    base = _gate_ability(actor, target); base["own_tempo_active"] = base["status"] == "resolved" and base["ability_id"] == "own-tempo" and not base["suppressed"]; return base


def _gate_cancelled_leaf(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], branch: Mapping[str, Any], caller_action_authority: Mapping[str, Any]) -> dict[str, Any]:
    return {"leaf_id": f"{row['action_id']}:cancelled:{branch['kind']}", "candidate_id": row["action_id"], "action_type": "attack", "branch_path": ("pre_action", branch["kind"]), "probability": deepcopy(branch["probability"]), "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "own_final_hp": actor["current_hp"]["current_hp"], "target_final_hp": target["current_hp"]["current_hp"], "target_ko": target["current_hp"]["current_hp"] == 0, "self_fainted": actor["current_hp"]["current_hp"] == 0, "secondary": None, "execution_failure": branch["kind"]}, "provenance": _leaf_provenance(row, caller_action_authority)}


def _confusion_self_hit_leaves(row: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], branch: Mapping[str, Any], caller_action_authority: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    direct = actor["direct_mechanics"].get("combatant", {})
    species, disguise = direct.get("species_id"), direct.get("disguise_state")
    if not isinstance(species, str) or disguise not in {None, "intact", "broken"}: return None
    values, stages = actor["current_final_stats"]["values"], actor["current_stages"]["values"]
    try:
        attack, defense = apply_boosts(values["attack"], stages["attack"]), apply_boosts(values["defense"], stages["defense"])
        base = ((((2 * actor["current_level"]["value"]) // 5 + 2) * 40 * attack) // defense) // 50 + 2
    except (KeyError, TypeError, ValueError, ZeroDivisionError): return None
    hp, mimikyu = actor["current_hp"]["current_hp"], species in {"mimikyu", "mimikyu-busted"}
    leaves=[]
    for index, factor in enumerate(range(85, 101)):
        raw = (base * factor) // 100; damage = 0 if mimikyu and disguise == "intact" else min(hp, raw); post = hp - damage
        leaves.append({"leaf_id": f"{row['action_id']}:confusion-self-hit:{index}", "candidate_id": row["action_id"], "action_type": "attack", "branch_path": ("pre_action", branch["kind"], f"self_hit_roll:{index}"), "probability": _fd(_fraction(branch["probability"]) * Fraction(1, 16)), "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": {"roll_index": index, "random_factor_percent": factor}, "consequences": {"damage": damage, "raw_damage": raw, "own_final_hp": post, "target_final_hp": target["current_hp"]["current_hp"], "self_fainted": post == 0, "target_ko": target["current_hp"]["current_hp"] == 0, "secondary": None, "selected_move_does_not_execute": True, "confusion_self_hit": {"base_power": 40, "type": "typeless", "category": "physical", "contact": False, "disguise_before": disguise, "disguise_after": "broken" if mimikyu and disguise == "intact" else disguise}}, "provenance": {**_leaf_provenance(row, caller_action_authority), "provenance": "canonical_detached_confusion_self_hit_v1"}})
    return leaves


def _cancelled(row: Mapping[str, Any], gate: Mapping[str, Any], caller_action_authority: Mapping[str, Any]) -> dict[str, Any]:
    actor = row["actor_mechanics"]; target = row["target_mechanics"]
    leaf = {"leaf_id": f"{row['action_id']}:cancelled:{gate['reason']}", "candidate_id": row["action_id"], "action_type": "attack", "branch_path": ("pre_action_cancelled", gate["reason"]), "probability": _fd(Fraction(1, 1)), "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "own_final_hp": actor["current_hp"]["current_hp"], "target_final_hp": target["current_hp"]["current_hp"], "target_ko": target["current_hp"]["current_hp"] == 0, "self_fainted": actor["current_hp"]["current_hp"] == 0, "secondary": None, "execution_failure": gate["reason"]}, "provenance": _leaf_provenance(row, caller_action_authority)}
    return {"status": "resolved", "schema_version": KERNEL_SCHEMA_VERSION, "execution_authority": deepcopy(dict(caller_action_authority)), "pre_action_gate": deepcopy(dict(gate)), "terminal_leaves": (leaf,), "terminal_probability_mass": _fd(Fraction(1, 1)), "provenance": "authenticated_standard_charge_shared_terminal_pre_action_cancellation_v1"}


def _leaf_provenance(row: Mapping[str, Any], caller_action_authority: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "attacker": deepcopy(row["actor"]),
        "target": deepcopy(row["target"]),
        "move_id": row["move_id"],
        "execution_authority": deepcopy(dict(caller_action_authority)),
    }
    source = caller_action_authority
    bindings = (
        ("session_id", "session_id"),
        ("source_runtime_fingerprint", "source_runtime_fingerprint"),
        ("source_branch_fingerprint", "source_branch_fingerprint"),
        ("decision_owner", "decision_owner"),
    )
    for output_key, source_key in bindings:
        if source_key in source:
            value[output_key] = deepcopy(source[source_key])
    return value


def _accuracy(base: int, accuracy_stage: int, evasion_stage: int) -> Fraction | None:
    if not isinstance(base, int) or not -6 <= accuracy_stage <= 6 or not -6 <= evasion_stage <= 6:
        return None
    stage = accuracy_stage - evasion_stage
    stage = max(-6, min(6, stage))
    multiplier = Fraction(3 + stage, 3) if stage >= 0 else Fraction(3, 3 - stage)
    return min(Fraction(1, 1), Fraction(base, 100) * multiplier)


def _field(field_fact: Mapping[str, Any], side_fact: Mapping[str, Any]) -> Field:
    value = side_fact.get("value", {})
    defender = SideField(reflect=bool(value.get("reflect", False)), light_screen=bool(value.get("light_screen", False)), aurora_veil=bool(value.get("aurora_veil", False)))
    weather = {"sandstorm": "sand"}.get(field_fact.get("weather"), field_fact.get("weather", "none"))
    return Field(weather=weather, terrain=field_fact.get("terrain", "none"), is_doubles=False, defender_side=defender)


def _volatiles(fact: Mapping[str, Any]) -> tuple[str, ...]:
    value = fact.get("value", fact.get("volatiles", ()))
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _fd(value: Fraction) -> dict[str, int]: return {"numerator": value.numerator, "denominator": value.denominator}
def _fraction(value: Mapping[str, Any]) -> Fraction: return Fraction(value["numerator"], value["denominator"])
def _incomplete(row: Mapping[str, Any], reason: str, caller_action_authority: Mapping[str, Any]) -> dict[str, Any]: return {"status": "incomplete", "schema_version": KERNEL_SCHEMA_VERSION, "reason": reason, "execution_authority": deepcopy(dict(caller_action_authority))}
def _value(value: Mapping[str, Any]) -> str | None: return value.get("value") if value.get("status") == "known" else None
def _condition(value: Mapping[str, Any]) -> str | None: return value.get("condition") if value.get("status") == "known_present" else None

