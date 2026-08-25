"""Materialize one exact first-action terminal leaf into detached state.

This owner is intentionally a projection boundary, not a second damage engine:
it reads an already-normalized terminal leaf and overlays only its exact
consequences on frozen D0 authority.  The output is never reducer authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "detached-predictive-intermediate-state-v1"
HORIZON = "immediate_action_pair"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STAGE_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")


def materialize_detached_predictive_intermediate_state(
    *, strategy_d0: Mapping[str, Any], terminal_leaf: Mapping[str, Any],
) -> dict[str, Any]:
    """Project exact leaf consequences without mutating D0 or runtime state."""
    base = _base(strategy_d0)
    if base is None:
        return _result("rejected", "invalid_runtime_strategy_d0", {})
    if isinstance(terminal_leaf, Mapping) and terminal_leaf.get("action_type") == "manual_switch":
        return _result("unsupported", "manual_switch_terminal_leaf_intermediate_state_adapter_unavailable", base)
    bound = _leaf_binding(terminal_leaf, strategy_d0)
    if isinstance(bound, str):
        return _result("rejected", bound, base)
    consequences = terminal_leaf.get("consequences")
    if not isinstance(consequences, Mapping):
        return _result("rejected", "terminal_leaf_consequences_missing", base)
    own_hp, target_hp = consequences.get("own_final_hp"), consequences.get("target_final_hp")
    if not _hp(own_hp) or not _hp(target_hp):
        return _result("incomplete", "terminal_leaf_exact_post_action_hp_missing", {**base, **bound})
    actor, target = bound["attacker"], bound["target"]
    stage_effects = _stage_effects(terminal_leaf, consequences)
    if isinstance(stage_effects, str):
        return _result("rejected", stage_effects, {**base, **bound})
    state = {
        "schema_version": SCHEMA_VERSION,
        "status": "resolved",
        "horizon": HORIZON,
        **base,
        "first_action": {
            "candidate_id": terminal_leaf["candidate_id"], "action_type": terminal_leaf["action_type"],
            "move_id": bound["move_id"], "leaf_id": terminal_leaf["leaf_id"],
            "branch_path": deepcopy(tuple(terminal_leaf["branch_path"])),
            "probability": deepcopy(dict(terminal_leaf["probability"])),
            "damage_roll": deepcopy(terminal_leaf.get("damage_roll")),
            "hit_state": terminal_leaf.get("hit_state"), "critical_state": terminal_leaf.get("critical_state"),
            "provenance": deepcopy(dict(terminal_leaf["provenance"])),
        },
        "active": {
            actor["side"]: _participant(strategy_d0, actor, own_hp, stage_effects, "self"),
            target["side"]: _participant(strategy_d0, target, target_hp, stage_effects, "target"),
        },
        "unchanged_authority": _unchanged_authority(strategy_d0),
        "second_action_compatibility": {
            "faint_cancellation": {
                "status": "resolved", "actor_can_act": own_hp > 0,
                "target_can_act": target_hp > 0,
                "rule": "second_selected_action_cancelled_if_its_actor_is_fainted",
            },
            "other_cancellation_mechanics": {
                "status": "unsupported", "reason": "flinch_disable_lock_and_related_cancellation_not_materialized_v1",
            },
        },
        "provenance": "exact_terminal_leaf_to_detached_intermediate_state_v1",
    }
    return state


def _participant(d0: Mapping[str, Any], owner: Mapping[str, Any], hp: int, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    current_stages = d0.get("current_stage_authority", {}).get(owner["side"], {})
    current_condition = d0.get("current_condition_authority", {}).get(owner["side"], {})
    return {
        "owner": deepcopy(dict(owner)),
        "hypothetical_hp": {"status": "known", "value": hp, "source": "exact_terminal_leaf"},
        "hypothetical_fainted": {"status": "known", "value": hp == 0, "source": "exact_terminal_leaf"},
        "current_stage_authority": deepcopy(current_stages),
        "hypothetical_stages": _stages(current_stages, effects, role),
        "current_condition_authority": deepcopy(current_condition),
        "hypothetical_condition": _condition(current_condition, effects, role),
    }


def _stages(authority: Any, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    source = authority.get("stages") if isinstance(authority, Mapping) else None
    result: dict[str, Any] = {}
    for stat in _STAGE_KEYS:
        current = source.get(stat) if isinstance(source, Mapping) else None
        value = {"status": "unknown", "reason": "current_stage_authority_unknown"}
        if isinstance(current, Mapping) and current.get("status") == "known":
            value = {"status": "known", "value": current.get("value"), "source": "frozen_current_stage_authority"}
        matching = [effect for effect in effects if effect.get("owner") == role and effect.get("stat") == stat]
        if matching:
            effect = matching[-1]
            resulting = effect.get("resulting_stage")
            if isinstance(resulting, int) and not isinstance(resulting, bool) and -6 <= resulting <= 6:
                value = {"status": "known", "value": resulting, "source": "exact_terminal_leaf_stage_effect", "effect": deepcopy(dict(effect))}
        result[stat] = value
    return result


def _condition(authority: Any, effects: tuple[Mapping[str, Any], ...], role: str) -> dict[str, Any]:
    current = authority.get("condition") if isinstance(authority, Mapping) else None
    result = deepcopy(dict(current)) if isinstance(current, Mapping) else {"status": "unknown", "reason": "current_condition_authority_unknown"}
    for effect in effects:
        condition = effect.get("hypothetical_target_condition")
        if role == "target" and isinstance(condition, Mapping) and isinstance(condition.get("resulting_condition"), str):
            return {"status": "known_present", "condition": condition["resulting_condition"], "source": "exact_terminal_leaf_condition_effect", "effect": deepcopy(dict(condition))}
    return result


def _stage_effects(leaf: Mapping[str, Any], consequences: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...] | str:
    result: list[Mapping[str, Any]] = []
    deterministic = consequences.get("deterministic_stage_effect")
    if isinstance(deterministic, Mapping):
        damage = consequences.get("damage")
        branches = deterministic.get("branches")
        matching = [row for row in branches if isinstance(row, Mapping) and row.get("raw_damage") == damage] if isinstance(branches, (tuple, list)) else []
        if len(matching) != 1 or not isinstance(matching[0].get("effects"), (tuple, list)):
            return "deterministic_stage_effect_leaf_identity_missing"
        result.extend(row for row in matching[0]["effects"] if isinstance(row, Mapping))
    secondary = consequences.get("secondary")
    if isinstance(secondary, Mapping) and secondary.get("branch") == "effect":
        stage = secondary.get("hypothetical_stage_effect")
        if isinstance(stage, Mapping): result.append(stage)
        condition = secondary.get("hypothetical_target_condition")
        if isinstance(condition, Mapping): result.append({"owner": "target", "hypothetical_target_condition": condition})
    return tuple(deepcopy(dict(effect)) for effect in result)


def _unchanged_authority(d0: Mapping[str, Any]) -> dict[str, Any]:
    current = d0.get("strategy_state", {}).get("current_state", {}).get("runtime_strategy_d0_authority", {})
    active = current.get("active") if isinstance(current, Mapping) else None
    field = current.get("field") if isinstance(current, Mapping) else None
    # Supported first-action leaves do not currently own type/item/ability or
    # field mutation.  Preserve only this narrow immutable authority summary.
    return {"status": "resolved", "active_current_authority": deepcopy(active) if isinstance(active, Mapping) else {}, "field_current_authority": deepcopy(field) if isinstance(field, Mapping) else {}, "carry_forward_rule": "only facts without a represented first_action consequence"}


def _leaf_binding(leaf: Any, d0: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(leaf, Mapping) or leaf.get("action_type") != "attack" or not isinstance(leaf.get("candidate_id"), str) or not isinstance(leaf.get("leaf_id"), str) or not isinstance(leaf.get("branch_path"), (tuple, list)) or not _fraction(leaf.get("probability")):
        return "invalid_terminal_leaf"
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping): return "terminal_leaf_provenance_missing"
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id")
    if any(key not in provenance for key in required): return "terminal_leaf_provenance_incomplete"
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    if any(provenance.get(key) != value for key, value in expected.items()): return "terminal_leaf_binding_mismatch"
    attacker, target = provenance["attacker"], provenance["target"]
    if not _owner(attacker) or not _owner(target) or attacker["side"] == target["side"] or d0.get("active_owners", {}).get(attacker["side"]) != dict(attacker) or d0.get("active_owners", {}).get(target["side"]) != dict(target): return "terminal_leaf_actor_target_identity_mismatch"
    if leaf["candidate_id"] != f"attack:{provenance['move_id']}": return "terminal_leaf_candidate_move_mismatch"
    return {"attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": provenance["move_id"]}


def _base(d0: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1" or not _owner(d0.get("decision_owner")) or not isinstance(d0.get("active_owners"), Mapping): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"]))}
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _fraction(value: Any) -> bool: return isinstance(value, Mapping) and isinstance(value.get("numerator"), int) and not isinstance(value.get("numerator"), bool) and isinstance(value.get("denominator"), int) and not isinstance(value.get("denominator"), bool) and 0 < value["denominator"] and 0 < value["numerator"] <= value["denominator"]
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
