"""Detached terminal execution for authenticated standard charge continuations.

This module deliberately has no runtime-D0 or reducer dependency.  A charge
move remains blocked by the generic immediate path; this owner is the sole
place where a continuation already authenticated at the next decision may be
represented as a terminal attack attempt.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_next_turn_predictive_mechanics_authority import validate_forced_continuation_predictive_mechanics_binding
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_detached_next_turn_held_item_effect_applicability import materialize_detached_next_turn_held_item_effect_applicability
from llm.advisor_detached_next_turn_sturdy_survival_authority import materialize_detached_next_turn_sturdy_survival_authority
from llm.advisor_detached_next_turn_focus_sash_survival_authority import materialize_detached_next_turn_focus_sash_survival_authority
from llm.advisor_detached_next_turn_life_orb_immediate_authority import materialize_detached_next_turn_life_orb_immediate_authority
from llm.advisor_standard_charge_terminal_execution import (
    CALLER_AUTH_SCHEMA_VERSION,
    FORCED_TURN_TWO_EXECUTION_MODE,
    execute_authenticated_terminal_mechanics_compatibility,
    execute_standard_charge_terminal_attack,
    materialize_standard_charge_terminal_execution_contract,
    standard_charge_terminal_missing_authority,
)
from llm.advisor_solar_terminal_weather_damage_modifier import (
    materialize_solar_terminal_weather_damage_modifier_authority,
)


AUTHORITY_SCHEMA_VERSION = "detached-standard-charge-turn-two-execution-authority-v1"
SCHEMA_VERSION = "detached-standard-charge-turn-two-attack-execution-v1"
_SIDES = ("self", "opponent")
_SOLAR_MOVES = frozenset({"solar-beam", "solar-blade"})
_SELF_EFFECT_MOVES = frozenset({"meteor-beam", "skull-bash"})
_SEMI_INVULNERABLE_MOVES = frozenset({"fly", "dig", "dive", "bounce"})


def materialize_detached_standard_charge_turn_two_execution_authority(*, next_decision_state: Mapping[str, Any], next_decision_fingerprint: str, forced_continuation: Mapping[str, Any], predictive_mechanics: Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate all forced actions without granting a generic charge bypass."""
    if not isinstance(next_decision_state, Mapping) or not isinstance(next_decision_fingerprint, str) or fingerprint_transition_preview_state(next_decision_state) != next_decision_fingerprint:
        return _result("rejected", "stale_or_invalid_next_decision_fingerprint")
    binding = validate_forced_continuation_predictive_mechanics_binding(forced_continuation=forced_continuation, predictive_mechanics=predictive_mechanics, next_decision_state=next_decision_state)
    if binding.get("status") != "resolved":
        return _result(binding.get("status", "rejected"), binding.get("reason", "forced_predictive_mechanics_binding_unavailable"))
    actions = forced_continuation.get("forced_continuation_actions", {})
    rows: dict[str, Any] = {}
    for side in _SIDES:
        action = actions.get(side)
        if not isinstance(action, Mapping) or action.get("status") == "known_none":
            rows[side] = {"status": "not_applicable", "reason": "no_forced_standard_charge_continuation"}
            continue
        if action.get("status") != "resolved" or side not in binding.get("bindings", {}):
            return _result("rejected", "forced_continuation_action_untrusted")
        row = _authority_row(side, action, binding["bindings"][side], next_decision_fingerprint)
        if isinstance(row, str):
            return _result("rejected", row)
        rows[side] = row
    return {"status": "resolved", "schema_version": AUTHORITY_SCHEMA_VERSION, "source_next_decision_fingerprint": next_decision_fingerprint, "next_decision_state": deepcopy(dict(next_decision_state)), "forced_continuation": deepcopy(dict(forced_continuation)), "predictive_mechanics": deepcopy(dict(predictive_mechanics)), "actions": rows, "provenance": "authenticated_forced_continuation_to_detached_turn_two_execution_authority_v1"}


def execute_detached_standard_charge_turn_two_attacks(*, execution_authority: Mapping[str, Any], pair_local_predictive_mechanics: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Materialize independent, unordered turn-two attack ledgers.

    The first vertical slice intentionally accepts only exact neutral detached
    mechanics.  Missing mechanics are represented as incomplete, never as a
    fabricated runtime snapshot or neutral default.
    """
    if not isinstance(execution_authority, Mapping) or execution_authority.get("status") != "resolved" or execution_authority.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        return _result("rejected", "standard_charge_turn_two_execution_authority_invalid")
    if not _authority_is_self_consistent(execution_authority):
        return _result("rejected", "standard_charge_turn_two_execution_authority_tampered")
    out: dict[str, Any] = {}
    for side, row in execution_authority.get("actions", {}).items():
        if row.get("status") == "not_applicable":
            out[side] = deepcopy(dict(row)); continue
        out[side] = _execute_one(row, execution_authority, pair_local_predictive_mechanics)
    result={"status": "resolved" if all(x.get("status") in {"resolved", "not_applicable"} for x in out.values()) else "incomplete", "schema_version": SCHEMA_VERSION, "source_next_decision_fingerprint": execution_authority["source_next_decision_fingerprint"], "execution_authority": deepcopy(dict(execution_authority)), "actions": out, "unordered": True, "provenance": "detached_standard_charge_turn_two_attack_attempt_v1"}
    if pair_local_predictive_mechanics is not None: result["pair_local_predictive_mechanics_authority"]=deepcopy(dict(pair_local_predictive_mechanics))
    return result


def validate_detached_standard_charge_turn_two_attack_execution(*, result: Any, execution_authority: Mapping[str, Any], pair_local_predictive_mechanics: Mapping[str, Any] | None = None) -> str | None:
    """Replay the entire detached charge result; provenance alone is not authority."""
    expected = execute_detached_standard_charge_turn_two_attacks(execution_authority=execution_authority, pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    return None if isinstance(result, Mapping) and deepcopy(dict(result)) == expected else "detached_standard_charge_turn_two_attack_execution_mismatch"


def _authority_row(side: str, action: Mapping[str, Any], bound: Mapping[str, Any], fingerprint: str) -> dict[str, Any] | str:
    if action.get("side") != side or action.get("lifecycle_state") != "turn_two_continuation_forced" or action.get("continuation_forced") is not True or action.get("execution_grant") is not False:
        return "forced_continuation_lifecycle_invalid"
    effect = resolve_canonical_standard_charge_turn_two_effect(action.get("move_id"))
    if effect.get("status") != "resolved": return "canonical_terminal_effect_unavailable"
    lifecycle = effect["lifecycle"]
    expected_family = (
        "weather_sensitive_charge_then_damage" if action.get("move_id") in _SOLAR_MOVES
        else "charge_turn_self_effect_then_damage" if action.get("move_id") in _SELF_EFFECT_MOVES
        else "semi_invulnerable_charge_then_damage" if action.get("move_id") in _SEMI_INVULNERABLE_MOVES
        else "ordinary_charge_then_damage"
    )
    if lifecycle.get("lifecycle_family") != expected_family or action.get("actor") != bound.get("actor") or action.get("resolved_target_owner") != bound.get("target"):
        return "forced_continuation_execution_identity_mismatch"
    return {"status": "resolved", "schema_version": AUTHORITY_SCHEMA_VERSION, "side": side, "source_next_decision_fingerprint": fingerprint, "actor": deepcopy(action["actor"]), "target": deepcopy(action["resolved_target_owner"]), "move_id": action["move_id"], "continuation_action_id": action["continuation_action_id"], "original_charge_action_id": action["original_charge_action_id"], "continuation_target_locator": deepcopy(action["continuation_target_locator"]), "original_charge_lifecycle": deepcopy(action["original_charge_provenance"]), **({"semi_invulnerable_charge_state_authority": deepcopy(dict(action["semi_invulnerable_charge_state_authority"]))} if isinstance(action.get("semi_invulnerable_charge_state_authority"), Mapping) else {}), "canonical_terminal_effect": effect, "predictive_actor_mechanics": deepcopy(bound["actor_mechanics"]), "predictive_target_mechanics": deepcopy(bound["target_mechanics"]), "execution_grant": "authenticated_standard_charge_turn_two_only", "provenance": "forced_continuation_and_predictive_mechanics_bound_execution_authority_v1"}


def materialize_detached_standard_charge_turn_two_terminal_execution_contract(
    *,
    execution_authority: Mapping[str, Any],
    side: str,
    pair_local_predictive_mechanics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Caller adapter: authenticate turn two, select mechanics, freeze supports."""
    if (
        not isinstance(execution_authority, Mapping)
        or execution_authority.get("status") != "resolved"
        or execution_authority.get("schema_version") != AUTHORITY_SCHEMA_VERSION
        or not _authority_is_self_consistent(execution_authority)
    ):
        return _result("rejected", "standard_charge_turn_two_execution_authority_invalid")
    row = execution_authority.get("actions", {}).get(side)
    if not isinstance(row, Mapping) or row.get("status") != "resolved":
        return _result("rejected", "standard_charge_turn_two_action_unavailable")

    actor = row["predictive_actor_mechanics"]
    target = row["predictive_target_mechanics"]
    if pair_local_predictive_mechanics is not None:
        from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import (
            validate_detached_next_turn_pair_local_predictive_mechanics,
        )
        if validate_detached_next_turn_pair_local_predictive_mechanics(
            authority=pair_local_predictive_mechanics,
            next_decision_state=execution_authority.get("next_decision_state"),
            next_decision_fingerprint=execution_authority.get("source_next_decision_fingerprint"),
        ) is not None:
            return {"status": "incomplete", "reason": "pair_local_predictive_mechanics_invalid"}
        sides = pair_local_predictive_mechanics.get("sides", {})
        actor = sides.get(row["actor"]["side"])
        target = sides.get(row["target"]["side"])
        if (
            not isinstance(actor, Mapping)
            or not isinstance(target, Mapping)
            or actor.get("owner") != row["actor"]
            or target.get("owner") != row["target"]
        ):
            return {"status": "incomplete", "reason": "pair_local_execution_identity_mismatch"}

    missing = standard_charge_terminal_missing_authority(actor) + standard_charge_terminal_missing_authority(target)
    if missing:
        return {
            "status": "incomplete",
            "reason": "detached_damage_mechanics_incomplete",
            "missing_authority": tuple(sorted(set(missing))),
        }

    move = row["canonical_terminal_effect"]["move"]
    terminal = _terminal_authorities(row, execution_authority, move, pair_local_predictive_mechanics)
    if terminal.get("status") != "resolved":
        return {"status": "incomplete", "reason": terminal.get("reason", "detached_terminal_authority_unavailable")}

    solar_modifier = materialize_solar_terminal_weather_damage_modifier_authority(
        move_id=row["move_id"],
        actor=row["actor"],
        target=row["target"],
        action_id=row["continuation_action_id"],
        source_state_fingerprint=execution_authority["source_next_decision_fingerprint"],
        actor_mechanics=actor,
    )
    if row["move_id"] in _SOLAR_MOVES and (
        not isinstance(solar_modifier, Mapping) or solar_modifier.get("status") != "resolved"
    ):
        return {"status": "incomplete", "reason": "solar_turn_two_terminal_weather_modifier_unavailable"}

    caller_authentication = _forced_turn_two_caller_authentication(
        execution_authority=execution_authority,
        row=row,
        actor_mechanics=actor,
        target_mechanics=target,
        terminal=terminal,
        solar_modifier=solar_modifier,
    )
    return materialize_standard_charge_terminal_execution_contract(
        execution_mode=FORCED_TURN_TWO_EXECUTION_MODE,
        source_state_fingerprint=execution_authority["source_next_decision_fingerprint"],
        decision_owner=row["actor"],
        actor=row["actor"],
        target=row["target"],
        action_id=row["continuation_action_id"],
        move_id=row["move_id"],
        canonical_terminal_effect=row["canonical_terminal_effect"],
        actor_mechanics=actor,
        target_mechanics=target,
        attacker_held_item_effect_authority=terminal["attacker_item"],
        target_held_item_effect_authority=terminal["target_item"],
        target_sturdy_authority=terminal["sturdy"],
        target_focus_sash_authority=terminal["focus_sash"],
        attacker_life_orb_authority=terminal["life_orb"],
        caller_action_authority=row,
        caller_authentication=caller_authentication,
        solar_terminal_weather_damage_modifier_authority=solar_modifier,
        semi_invulnerable_charge_state_authority=row.get("semi_invulnerable_charge_state_authority"),
    )


def validate_detached_standard_charge_turn_two_terminal_execution_contract(
    *,
    contract: Any,
    execution_authority: Mapping[str, Any],
    side: str,
    pair_local_predictive_mechanics: Mapping[str, Any] | None = None,
) -> str | None:
    """Replay the caller-specific adapter; shared kernel stays lifecycle-neutral."""
    expected = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=execution_authority,
        side=side,
        pair_local_predictive_mechanics=pair_local_predictive_mechanics,
    )
    return (
        None
        if isinstance(contract, Mapping) and deepcopy(dict(contract)) == expected
        else "detached_standard_charge_turn_two_terminal_execution_contract_mismatch"
    )


def _execute_one(row: Mapping[str, Any], execution_authority: Mapping[str, Any], pair_local_predictive_mechanics: Mapping[str, Any] | None = None) -> dict[str, Any]:
    # Backward-compatible private entry used by detached ordinary attacks.
    if execution_authority.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        actor, target = row["predictive_actor_mechanics"], row["predictive_target_mechanics"]
        if pair_local_predictive_mechanics is not None:
            from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import validate_detached_next_turn_pair_local_predictive_mechanics
            if validate_detached_next_turn_pair_local_predictive_mechanics(
                authority=pair_local_predictive_mechanics,
                next_decision_state=execution_authority.get("next_decision_state"),
                next_decision_fingerprint=execution_authority.get("source_next_decision_fingerprint"),
            ) is not None:
                return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "pair_local_predictive_mechanics_invalid", "execution_authority": deepcopy(dict(row))}
            sides = pair_local_predictive_mechanics.get("sides", {})
            actor, target = sides.get(row["actor"]["side"]), sides.get(row["target"]["side"])
            if not isinstance(actor, Mapping) or not isinstance(target, Mapping) or actor.get("owner") != row["actor"] or target.get("owner") != row["target"]:
                return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "pair_local_execution_identity_mismatch", "execution_authority": deepcopy(dict(row))}
        missing = standard_charge_terminal_missing_authority(actor) + standard_charge_terminal_missing_authority(target)
        if missing:
            return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "detached_damage_mechanics_incomplete", "missing_authority": tuple(sorted(set(missing))), "execution_authority": deepcopy(dict(row))}
        terminal = _terminal_authorities(row, execution_authority, row["canonical_terminal_effect"]["move"], pair_local_predictive_mechanics)
        if terminal.get("status") != "resolved":
            return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": terminal.get("reason", "detached_terminal_authority_unavailable"), "execution_authority": deepcopy(dict(row))}
        result = execute_authenticated_terminal_mechanics_compatibility(
            row=row,
            actor_mechanics=actor,
            target_mechanics=target,
            terminal_authorities=terminal,
        )
        result = deepcopy(dict(result))
        result["schema_version"] = SCHEMA_VERSION
        return result

    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=execution_authority,
        side=row["side"],
        pair_local_predictive_mechanics=pair_local_predictive_mechanics,
    )
    if contract.get("status") != "resolved":
        result = {
            "status": "incomplete",
            "schema_version": SCHEMA_VERSION,
            "reason": contract.get("reason", "standard_charge_terminal_contract_unavailable"),
            "execution_authority": deepcopy(dict(row)),
        }
        if "missing_authority" in contract:
            result["missing_authority"] = deepcopy(contract["missing_authority"])
        return result
    kernel = execute_standard_charge_terminal_attack(execution_contract=contract)
    return _legacy_kernel_result(kernel)


def _legacy_kernel_result(kernel: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(kernel))
    result["schema_version"] = SCHEMA_VERSION
    if result.get("status") == "resolved":
        result["provenance"] = (
            "authenticated_detached_standard_charge_turn_two_exact_attack_ledger_v1"
            if "component_manifest" in result
            else "detached_standard_charge_pre_action_cancellation_v1"
        )
    return result


def _forced_turn_two_caller_authentication(
    *,
    execution_authority: Mapping[str, Any],
    row: Mapping[str, Any],
    actor_mechanics: Mapping[str, Any],
    target_mechanics: Mapping[str, Any],
    terminal: Mapping[str, Any],
    solar_modifier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CALLER_AUTH_SCHEMA_VERSION,
        "caller_kind": "forced_turn_two_continuation",
        "execution_mode": FORCED_TURN_TWO_EXECUTION_MODE,
        "session_id": row["actor"]["session_id"],
        "source_state_fingerprint": execution_authority["source_next_decision_fingerprint"],
        "decision_owner": deepcopy(dict(row["actor"])),
        "actor": deepcopy(dict(row["actor"])),
        "target": deepcopy(dict(row["target"])),
        "action_id": row["continuation_action_id"],
        "move_id": row["move_id"],
        "canonical_terminal_effect": deepcopy(dict(row["canonical_terminal_effect"])),
        "actor_mechanics": deepcopy(dict(actor_mechanics)),
        "target_mechanics": deepcopy(dict(target_mechanics)),
        "attacker_held_item_effect_authority": deepcopy(dict(terminal["attacker_item"])),
        "target_held_item_effect_authority": deepcopy(dict(terminal["target_item"])),
        "target_sturdy_authority": deepcopy(dict(terminal["sturdy"])),
        "target_focus_sash_authority": deepcopy(dict(terminal["focus_sash"])),
        "attacker_life_orb_authority": deepcopy(dict(terminal["life_orb"])),
        "caller_action_authority": deepcopy(dict(row)),
        "power_herb_consumption_authority": None,
        **({"semi_invulnerable_charge_state_authority": deepcopy(dict(row["semi_invulnerable_charge_state_authority"]))} if isinstance(row.get("semi_invulnerable_charge_state_authority"), Mapping) else {}),
        **({"solar_terminal_weather_damage_modifier_authority": deepcopy(dict(solar_modifier))} if isinstance(solar_modifier, Mapping) else {}),
        "source_execution_authority": deepcopy(dict(execution_authority)),
        "provenance": "forced_turn_two_standard_charge_terminal_caller_authentication_v1",
    }


def _terminal_authorities(row: Mapping[str, Any], execution: Mapping[str, Any], move: Mapping[str, Any], pair_local_predictive_mechanics: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state, fingerprint, predictive = execution.get("next_decision_state"), execution.get("source_next_decision_fingerprint"), execution.get("predictive_mechanics")
    action = {"action_type": "attack", "action_id": row["continuation_action_id"], "identity": row["move_id"]}
    attacker_item = materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, holder=row["actor"], pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    target_item = materialize_detached_next_turn_held_item_effect_applicability(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, holder=row["target"], pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    if attacker_item.get("status") != "resolved" or target_item.get("status") != "resolved": return {"status": "incomplete", "reason": "detached_held_item_effect_applicability_unavailable"}
    if attacker_item.get("terminal_consumption") == "required_unrepresented" or target_item.get("terminal_consumption") == "required_unrepresented": return {"status": "incomplete", "reason": "detached_terminal_consumable_item_consequence_unrepresented"}
    sturdy = materialize_detached_next_turn_sturdy_survival_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, defender=row["target"], attacker=row["actor"], action=action, move_metadata=move, pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    sash = materialize_detached_next_turn_focus_sash_survival_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, holder=row["target"], attacker=row["actor"], action=action, move_metadata=move, held_item_effect_applicability=target_item, pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    life = materialize_detached_next_turn_life_orb_immediate_authority(next_decision_state=state, next_decision_fingerprint=fingerprint, predictive_mechanics=predictive, attacker=row["actor"], target=row["target"], action=action, move_metadata=move, qualifying_damage=True, held_item_effect_applicability=attacker_item, pair_local_predictive_mechanics=pair_local_predictive_mechanics)
    if sturdy.get("status") in {"incomplete", "rejected"}: return {"status": "incomplete", "reason": "detached_sturdy_survival_authority_unavailable"}
    if sash.get("status") in {"incomplete", "rejected"}: return {"status": "incomplete", "reason": "detached_focus_sash_survival_authority_unavailable"}
    if life.get("status") in {"incomplete", "rejected"}: return {"status": "incomplete", "reason": "detached_life_orb_authority_unavailable"}
    return {"status": "resolved", "attacker_item": attacker_item, "target_item": target_item, "sturdy": sturdy, "focus_sash": sash, "life_orb": life}


def _authority_is_self_consistent(authority: Mapping[str, Any]) -> bool:
    """Detect post-materialization mutation without treating metadata as authority.

    Full replay is intentionally performed by materialization (where the next
    decision state exists); this local check prevents an altered bound row from
    silently becoming executable after that authentication boundary.
    """
    forced, predictive, actions, state = authority.get("forced_continuation"), authority.get("predictive_mechanics"), authority.get("actions"), authority.get("next_decision_state")
    if not isinstance(forced, Mapping) or not isinstance(predictive, Mapping) or not isinstance(actions, Mapping) or not isinstance(state, Mapping) or fingerprint_transition_preview_state(state) != authority.get("source_next_decision_fingerprint"):
        return False
    source_actions, source_sides = forced.get("forced_continuation_actions"), predictive.get("sides")
    if not isinstance(source_actions, Mapping) or not isinstance(source_sides, Mapping):
        return False
    for side in _SIDES:
        row = actions.get(side)
        if not isinstance(row, Mapping):
            return False
        if row.get("status") == "not_applicable":
            if not isinstance(source_actions.get(side), Mapping) or source_actions[side].get("status") != "known_none":
                return False
            continue
        source = source_actions.get(side)
        other = "opponent" if side == "self" else "self"
        if not isinstance(source, Mapping) or row.get("actor") != source.get("actor") or row.get("target") != source.get("resolved_target_owner") or row.get("move_id") != source.get("move_id") or row.get("continuation_action_id") != source.get("continuation_action_id") or row.get("original_charge_action_id") != source.get("original_charge_action_id") or row.get("predictive_actor_mechanics") != source_sides.get(side) or row.get("predictive_target_mechanics") != source_sides.get(other):
            return False
        if row.get("canonical_terminal_effect") != resolve_canonical_standard_charge_turn_two_effect(source.get("move_id")):
            return False
    return True


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": AUTHORITY_SCHEMA_VERSION, "reason": reason}
