"""Detached exact semi-invulnerable charge state and targetability owners."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle
from advisor.damage.q12 import Q12_ONE
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_d0_locked_on_gravity_authority import (
    freeze_runtime_d0_locked_on_target_binding_authority,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


STATE_SCHEMA = "detached-semi-invulnerable-charge-state-authority-v1"
TARGETABILITY_SCHEMA = "detached-semi-invulnerable-targetability-authority-v1"
MODIFIER_SCHEMA = "detached-semi-invulnerable-exception-damage-modifier-authority-v1"
RETIREMENT_SCHEMA = "detached-semi-invulnerable-state-retirement-authority-v1"

_MOVE_CLASS = {
    "fly": "airborne",
    "bounce": "airborne",
    "dig": "underground",
    "dive": "underwater",
}
_EXCEPTIONS = {
    "airborne": {
        "gust": 2, "twister": 2, "sky-uppercut": 1, "thunder": 1,
        "hurricane": 1, "smack-down": 1, "thousand-arrows": 1,
    },
    "underground": {"earthquake": 2, "magnitude": 2},
    "underwater": {"surf": 2, "whirlpool": 2},
}
_STATE_ENDING_AIRBORNE = frozenset({"smack-down", "thousand-arrows"})
_OWNER_KEYS = frozenset({"session_id", "side", "slot_index", "pokemon_id"})


def materialize_detached_semi_invulnerable_charge_state_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    action_id: str,
    move_id: str,
    source_leaf_id: str,
) -> dict[str, Any]:
    """Materialize path-local state only after one authenticated charge-start leaf."""
    if not _valid_d0_binding(strategy_d0, runtime_snapshot, actor, target):
        return _result("rejected", STATE_SCHEMA, "semi_invulnerable_state_binding_invalid")
    if move_id not in _MOVE_CLASS or not isinstance(action_id, str) or not action_id or not isinstance(source_leaf_id, str) or not source_leaf_id:
        return _result("rejected", STATE_SCHEMA, "semi_invulnerable_state_source_invalid")
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    if (
        lifecycle.get("status") != "resolved"
        or lifecycle.get("lifecycle_family") != "semi_invulnerable_charge_then_damage"
        or lifecycle.get("execution_model") != "semi_invulnerable_then_execute"
        or lifecycle.get("semi_invulnerability_class") != _MOVE_CLASS[move_id]
        or lifecycle.get("protection_bypass_later_execution") is not False
    ):
        return _result("rejected", STATE_SCHEMA, "semi_invulnerable_canonical_lifecycle_invalid")
    return {
        "status": "resolved",
        "schema_version": STATE_SCHEMA,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "owner": deepcopy(dict(actor)),
        "original_target": deepcopy(dict(target)),
        "source_action_id": action_id,
        "source_move_id": move_id,
        "canonical_lifecycle": deepcopy(dict(lifecycle)),
        "semi_invulnerability_class": _MOVE_CLASS[move_id],
        "state": "active",
        "source_leaf_id": source_leaf_id,
        "entered_after_pre_action_gate": True,
        "hypothetical": True,
        "observation_emitted": False,
        "provenance": "authenticated_charge_start_leaf_to_detached_semi_invulnerable_state_v1",
    }


def validate_detached_semi_invulnerable_charge_state_authority(
    authority: Any,
    *,
    strategy_d0: Mapping[str, Any] | None = None,
    runtime_snapshot: Mapping[str, Any] | None = None,
) -> str | None:
    if not isinstance(authority, Mapping) or authority.get("schema_version") != STATE_SCHEMA or authority.get("status") != "resolved":
        return "semi_invulnerable_state_authority_invalid"
    move_id, cls = authority.get("source_move_id"), authority.get("semi_invulnerability_class")
    if move_id not in _MOVE_CLASS or cls != _MOVE_CLASS[move_id] or cls == "vanished":
        return "semi_invulnerable_state_class_invalid"
    if authority.get("state") != "active" or authority.get("hypothetical") is not True or authority.get("observation_emitted") is not False or authority.get("entered_after_pre_action_gate") is not True:
        return "semi_invulnerable_state_semantics_invalid"
    action_id = authority.get("source_action_id")
    source_leaf_id = authority.get("source_leaf_id")
    if not isinstance(action_id, str) or not action_id or not isinstance(source_leaf_id, str) or source_leaf_id != f"{action_id}:charge-start":
        return "semi_invulnerable_state_source_action_binding_invalid"
    if not _owner(authority.get("owner")) or not _owner(authority.get("original_target")) or authority["owner"]["side"] == authority["original_target"]["side"]:
        return "semi_invulnerable_state_identity_invalid"
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    if authority.get("canonical_lifecycle") != lifecycle:
        return "semi_invulnerable_state_lifecycle_mismatch"
    if strategy_d0 is not None and runtime_snapshot is not None:
        expected = materialize_detached_semi_invulnerable_charge_state_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            actor=authority["owner"], target=authority["original_target"],
            action_id=authority.get("source_action_id"), move_id=move_id,
            source_leaf_id=authority.get("source_leaf_id"),
        )
        if expected != dict(authority):
            return "semi_invulnerable_state_authority_mismatch"
    return None


def freeze_detached_semi_invulnerable_targetability_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    incoming_action: Mapping[str, Any],
    incoming_move_metadata_authority: Mapping[str, Any],
    attacker: Mapping[str, Any],
    target: Mapping[str, Any],
    semi_invulnerable_state_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve targetability before accuracy, never using damage as a proxy."""
    if not _valid_active_pair_binding(strategy_d0, runtime_snapshot, attacker, target):
        return _result("rejected", TARGETABILITY_SCHEMA, "semi_targetability_d0_binding_invalid")
    error = validate_detached_semi_invulnerable_charge_state_authority(semi_invulnerable_state_authority)
    if error is not None:
        return _result("rejected", TARGETABILITY_SCHEMA, error)
    if semi_invulnerable_state_authority.get("owner") != target:
        return _result("rejected", TARGETABILITY_SCHEMA, "semi_targetability_target_identity_mismatch")
    metadata = incoming_move_metadata_authority.get("metadata") if isinstance(incoming_move_metadata_authority, Mapping) else None
    move_id = metadata.get("move_id") if isinstance(metadata, Mapping) else None
    action_move_id = incoming_action.get("identity") if isinstance(incoming_action, Mapping) and isinstance(incoming_action.get("identity"), str) else incoming_action.get("move_id") if isinstance(incoming_action, Mapping) else None
    if (
        not isinstance(incoming_action, Mapping)
        or incoming_action.get("action_type") != "attack"
        or action_move_id != move_id
        or not isinstance(incoming_action.get("action_id"), str)
        or incoming_move_metadata_authority.get("status") != "resolved"
    ):
        return _result("incomplete", TARGETABILITY_SCHEMA, "incoming_move_metadata_unavailable")

    if not isinstance(move_id, str) or not move_id:
        return _result("incomplete", TARGETABILITY_SCHEMA, "incoming_move_metadata_unavailable")
    cls = semi_invulnerable_state_authority["semi_invulnerability_class"]
    exception = _EXCEPTIONS.get(cls, {}).get(move_id)
    base = {
        "schema_version": TARGETABILITY_SCHEMA,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)),
        "incoming_action_id": incoming_action["action_id"],
        "incoming_move_id": move_id,
        "incoming_move_metadata_authority": deepcopy(dict(incoming_move_metadata_authority)),
        "semi_invulnerable_state_authority": deepcopy(dict(semi_invulnerable_state_authority)),
        "semi_invulnerability_class": cls,
    }
    if exception is not None:
        return {
            "status": "resolved", **base,
            "outcome": "allowed_by_exact_exception",
            "exception_multiplier": exception,
            "state_cancel_after_successful_hit": cls == "airborne" and move_id in _STATE_ENDING_AIRBORNE,
            "accuracy_bypassed": False,
            "provenance": "canonical_semi_invulnerable_exception_targetability_v1",
        }

    abilities = _exact_no_guard_state(runtime_snapshot, attacker, target)
    if abilities["status"] == "rejected":
        return _result("rejected", TARGETABILITY_SCHEMA, abilities["reason"])
    if abilities["status"] == "resolved" and abilities["no_guard"] is True:
        return {
            "status": "resolved", **base,
            "outcome": "allowed_by_no_guard", "exception_multiplier": 1,
            "state_cancel_after_successful_hit": False, "accuracy_bypassed": True,
            "no_guard_authority": abilities,
            "provenance": "exact_no_guard_semi_invulnerable_bypass_v1",
        }

    locked = freeze_runtime_d0_locked_on_target_binding_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, source_owner=attacker,
    )
    if locked.get("status") == "rejected":
        return _result("rejected", TARGETABILITY_SCHEMA, locked.get("reason", "locked_on_authority_rejected"))
    if locked.get("status") == "resolved" and locked.get("locked_on_state", {}).get("status") == "known_active":
        if locked["locked_on_state"].get("bound_target") == dict(target):
            return {
                "status": "resolved", **base,
                "outcome": "allowed_by_locked_on", "exception_multiplier": 1,
                "state_cancel_after_successful_hit": False, "accuracy_bypassed": True,
                "locked_on_target_binding_authority": deepcopy(dict(locked)),
                "provenance": "exact_locked_on_semi_invulnerable_bypass_v1",
            }
    if abilities["status"] != "resolved":
        return {**_result("incomplete", TARGETABILITY_SCHEMA, "relevant_no_guard_ability_unknown"), **base}
    if locked.get("status") == "incomplete":
        return {**_result("incomplete", TARGETABILITY_SCHEMA, "current_locked_on_state_unknown"), **base}
    return {
        "status": "resolved", **base,
        "outcome": "blocked_by_semi_invulnerability", "exception_multiplier": None,
        "state_cancel_after_successful_hit": False, "accuracy_bypassed": False,
        "locked_on_target_binding_authority": deepcopy(dict(locked)),
        "no_guard_authority": abilities,
        "provenance": "canonical_semi_invulnerable_block_v1",
    }


def materialize_detached_next_turn_semi_invulnerable_targetability_authority(
    *,
    source_next_decision_fingerprint: str,
    incoming_action_intent: Mapping[str, Any],
    attacker_mechanics: Mapping[str, Any],
    target_mechanics: Mapping[str, Any],
    semi_invulnerable_state_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve one next-turn incoming intent against carried semi-invulnerability.

    Exception moves and exact No Guard are independently sufficient.  A
    non-exception attack remains incomplete when no exact next-turn Locked On
    fact is supplied; missing is never treated as inactive.
    """
    error = validate_detached_semi_invulnerable_charge_state_authority(
        semi_invulnerable_state_authority,
    )
    if error is not None:
        return _result("rejected", TARGETABILITY_SCHEMA, error)
    if not isinstance(source_next_decision_fingerprint, str) or not source_next_decision_fingerprint:
        return _result("rejected", TARGETABILITY_SCHEMA, "next_turn_targetability_fingerprint_invalid")
    if not isinstance(incoming_action_intent, Mapping) or incoming_action_intent.get("status") != "resolved":
        return _result("rejected", TARGETABILITY_SCHEMA, "next_turn_incoming_action_intent_invalid")
    attacker = incoming_action_intent.get("actor")
    target = incoming_action_intent.get("target")
    move_id = incoming_action_intent.get("move_id")
    if (
        not _owner(attacker) or not _owner(target)
        or target != semi_invulnerable_state_authority.get("owner")
        or attacker.get("side") == target.get("side")
        or not isinstance(move_id, str) or not move_id
        or attacker_mechanics.get("owner") != attacker
        or target_mechanics.get("owner") != target
    ):
        return _result("rejected", TARGETABILITY_SCHEMA, "next_turn_targetability_identity_mismatch")
    cls = semi_invulnerable_state_authority["semi_invulnerability_class"]
    base = {
        "schema_version": TARGETABILITY_SCHEMA,
        "session_id": target["session_id"],
        "source_runtime_fingerprint": semi_invulnerable_state_authority["source_runtime_fingerprint"],
        "source_branch_fingerprint": semi_invulnerable_state_authority["source_branch_fingerprint"],
        "source_next_decision_fingerprint": source_next_decision_fingerprint,
        "decision_owner": deepcopy(semi_invulnerable_state_authority["decision_owner"]),
        "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)),
        "incoming_action_id": incoming_action_intent["action_id"],
        "incoming_move_id": move_id,
        "semi_invulnerable_state_authority": deepcopy(dict(semi_invulnerable_state_authority)),
        "semi_invulnerability_class": cls,
    }
    exception = _EXCEPTIONS.get(cls, {}).get(move_id)
    if exception is not None:
        return {
            "status": "resolved", **base,
            "outcome": "allowed_by_exact_exception",
            "exception_multiplier": exception,
            "state_cancel_after_successful_hit": cls == "airborne" and move_id in _STATE_ENDING_AIRBORNE,
            "accuracy_bypassed": False,
            "provenance": "canonical_next_turn_semi_invulnerable_exception_targetability_v1",
        }
    attacker_ability = attacker_mechanics.get("ability")
    target_ability = target_mechanics.get("ability")
    known_abilities = []
    for row in (attacker_ability, target_ability):
        if not isinstance(row, Mapping) or row.get("status") not in {"known", "known_absent"}:
            return {**_result("incomplete", TARGETABILITY_SCHEMA, "relevant_no_guard_ability_unknown"), **base}
        known_abilities.append(row.get("value") if row.get("status") == "known" else None)
    if "no-guard" in known_abilities:
        return {
            "status": "resolved", **base,
            "outcome": "allowed_by_no_guard", "exception_multiplier": 1,
            "state_cancel_after_successful_hit": False, "accuracy_bypassed": True,
            "provenance": "exact_next_turn_no_guard_semi_invulnerable_bypass_v1",
        }
    # A current-D0 Locked On fact must not be promoted across the EOT boundary.
    # Until a next-decision temporal Locked On owner exists, non-exception
    # targetability remains unknown rather than treating the old fact as current.
    return {**_result("incomplete", TARGETABILITY_SCHEMA, "next_turn_locked_on_temporal_authority_unavailable"), **base}


def materialize_semi_invulnerable_exception_damage_modifier_authority(
    targetability_authority: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(targetability_authority, Mapping) or targetability_authority.get("schema_version") != TARGETABILITY_SCHEMA or targetability_authority.get("status") != "resolved":
        return None
    if targetability_authority.get("outcome") != "allowed_by_exact_exception":
        return None
    multiplier = targetability_authority.get("exception_multiplier")
    if multiplier not in {1, 2}:
        return None
    return {
        "status": "resolved",
        "schema_version": MODIFIER_SCHEMA,
        "session_id": targetability_authority["session_id"],
        "source_runtime_fingerprint": targetability_authority["source_runtime_fingerprint"],
        "source_branch_fingerprint": targetability_authority["source_branch_fingerprint"],
        "attacker": deepcopy(targetability_authority["attacker"]),
        "target": deepcopy(targetability_authority["target"]),
        "incoming_move_id": targetability_authority["incoming_move_id"],
        "semi_invulnerability_class": targetability_authority["semi_invulnerability_class"],
        "source_targetability_authority": deepcopy(dict(targetability_authority)),
        "modifier_q12": Q12_ONE * multiplier,
        "multiplier": {"numerator": multiplier, "denominator": 1},
        "modifier_stage": "final_damage_modifier_before_random_roll_resolution",
        "provenance": "authenticated_semi_invulnerable_exception_damage_modifier_v1",
    }


def materialize_semi_invulnerable_state_retirement(
    *,
    active_state_authority: Mapping[str, Any],
    source_leaf_id: str,
    reason: str,
) -> dict[str, Any]:
    error = validate_detached_semi_invulnerable_charge_state_authority(active_state_authority)
    if error is not None or not isinstance(source_leaf_id, str) or not source_leaf_id or not isinstance(reason, str) or not reason:
        return _result("rejected", RETIREMENT_SCHEMA, error or "semi_invulnerable_retirement_binding_invalid")
    return {
        "status": "resolved",
        "schema_version": RETIREMENT_SCHEMA,
        "owner": deepcopy(active_state_authority["owner"]),
        "source_action_id": active_state_authority["source_action_id"],
        "source_move_id": active_state_authority["source_move_id"],
        "semi_invulnerability_class": active_state_authority["semi_invulnerability_class"],
        "state_before": "active",
        "state_after": "inactive",
        "source_leaf_id": source_leaf_id,
        "reason": reason,
        "source_state_authority": deepcopy(dict(active_state_authority)),
        "hypothetical": True,
        "observation_emitted": False,
        "provenance": "authenticated_detached_semi_invulnerable_state_retirement_v1",
    }


def _exact_no_guard_state(runtime_snapshot: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    rows = {}
    for label, owner in (("attacker", attacker), ("target", target)):
        row = _pokemon(state, owner)
        ability = row.get("current_ability") if isinstance(row, Mapping) else None
        provenance = row.get("current_ability_provenance") if isinstance(row, Mapping) else None
        if is_unknown_battle_fact(ability) or ability is None:
            rows[label] = {"status": "unknown"}
            continue
        trusted = (
            isinstance(ability, str) and bool(ability) and isinstance(provenance, Mapping)
            and (
                (provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation")
                or (provenance.get("event_kind") == "switch_entry_ability_transition_derived" and provenance.get("trust") == "mechanics_derived_runtime")
            )
        )
        if not trusted:
            rows[label] = {"status": "unknown"}
        else:
            rows[label] = {"status": "known", "ability": ability, "source_provenance": deepcopy(dict(provenance))}
    if any(row["status"] == "known" and row.get("ability") == "no-guard" for row in rows.values()):
        return {"status": "resolved", "no_guard": True, **rows}
    if all(row["status"] == "known" for row in rows.values()):
        return {"status": "resolved", "no_guard": False, **rows}
    return {"status": "incomplete", "reason": "relevant_no_guard_ability_unknown", "no_guard": None, **rows}


def _valid_active_pair_binding(d0: Any, snapshot: Any, actor: Any, target: Any) -> bool:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return False
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(actor["side"]) != dict(actor) or active.get(target["side"]) != dict(target):
        return False
    return runtime_strategy_d0_freshness(strategy_d0=d0, runtime_snapshot=snapshot).get("status") == "current"


def _valid_d0_binding(d0: Any, snapshot: Any, actor: Any, target: Any) -> bool:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(actor) or not _owner(target) or actor.get("side") == target.get("side"):
        return False
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(actor["side"]) != dict(actor) or active.get(target["side"]) != dict(target):
        return False
    if actor != d0.get("decision_owner"):
        return False
    return runtime_strategy_d0_freshness(strategy_d0=d0, runtime_snapshot=snapshot).get("status") == "current"


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner["slot_index"], roster.get(str(owner["slot_index"]))) if isinstance(roster, Mapping) else None
    return row if isinstance(row, Mapping) and row.get("pokemon_id") == owner["pokemon_id"] else None


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and set(value) == _OWNER_KEYS
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _result(status: str, schema: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": schema, "reason": reason}
