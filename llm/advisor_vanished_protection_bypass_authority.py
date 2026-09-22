"""Strict Phantom Force / Shadow Force protection bypass and break authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle
from llm.advisor_hypothetical_protection_effects import canonical_protection_success_chain_metadata


SCHEMA_VERSION = "detached-vanished-protection-bypass-break-authority-v1"
_SUPPORTED_MOVES = frozenset({"phantom-force", "shadow-force"})
_SUPPORTED_PROTECTION_FAMILIES = frozenset({
    "ordinary", "silk_trap", "kings_shield", "obstruct",
    "spiky_shield", "baneful_bunker", "burning_bulwark",
})
_OWNER_KEYS = frozenset({"session_id", "side", "slot_index", "pokemon_id"})


def materialize_vanished_protection_bypass_break_authority(
    *,
    session_id: str,
    source_runtime_fingerprint: str,
    source_branch_fingerprint: str,
    decision_owner: Mapping[str, Any],
    attacker: Mapping[str, Any],
    protected_target: Mapping[str, Any],
    source_action_id: str,
    move_id: str,
    source_terminal_leaf_id: str,
    active_protection_effect: Mapping[str, Any],
    protection_action_authority: Mapping[str, Any],
    protection_context_fingerprint: str,
) -> dict[str, Any]:
    """Authenticate one terminal vanished attack bypassing one exact protection."""
    if (
        not isinstance(session_id, str) or not session_id
        or not isinstance(source_runtime_fingerprint, str) or not source_runtime_fingerprint
        or not isinstance(source_branch_fingerprint, str) or not source_branch_fingerprint
        or not _owner(decision_owner) or not _owner(attacker) or not _owner(protected_target)
        or attacker.get("session_id") != session_id or protected_target.get("session_id") != session_id
        or attacker.get("side") == protected_target.get("side")
        or not isinstance(source_action_id, str) or not source_action_id
        or not isinstance(source_terminal_leaf_id, str) or not source_terminal_leaf_id
        or not source_terminal_leaf_id.startswith(f"{source_action_id}:")
        or not isinstance(protection_context_fingerprint, str) or not protection_context_fingerprint
        or move_id not in _SUPPORTED_MOVES
    ):
        return _result("rejected", "vanished_protection_bypass_binding_invalid")
    lifecycle = resolve_canonical_charge_move_lifecycle(move_id)
    if (
        lifecycle.get("status") != "resolved"
        or lifecycle.get("lifecycle_family") != "semi_invulnerable_charge_then_damage"
        or lifecycle.get("execution_model") != "semi_invulnerable_then_execute"
        or lifecycle.get("semi_invulnerability_class") != "vanished"
        or lifecycle.get("protection_bypass_later_execution") is not True
    ):
        return _result("rejected", "vanished_protection_bypass_canonical_lifecycle_invalid")
    if (
        not isinstance(active_protection_effect, Mapping)
        or active_protection_effect.get("status") != "resolved"
        or active_protection_effect.get("owner") != protected_target
    ):
        return _result("rejected", "vanished_protection_effect_owner_mismatch")
    metadata = active_protection_effect.get("metadata")
    protection_move_id = metadata.get("move_id") if isinstance(metadata, Mapping) else None
    action_error = _protection_action_error(
        protection_action_authority, protected_target, attacker,
        protection_move_id, protection_context_fingerprint,
    )
    if action_error is not None:
        return _result("rejected", action_error)
    canonical = canonical_protection_success_chain_metadata(protection_move_id)
    if not isinstance(canonical, Mapping) or canonical.get("family") not in _SUPPORTED_PROTECTION_FAMILIES:
        return _result("unsupported", "vanished_protection_family_unrepresented")
    if canonical.get("metadata") != metadata:
        return _result("rejected", "vanished_protection_metadata_mismatch")
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "source_runtime_fingerprint": source_runtime_fingerprint,
        "source_branch_fingerprint": source_branch_fingerprint,
        "decision_owner": deepcopy(dict(decision_owner)),
        "attacker": deepcopy(dict(attacker)),
        "protected_target": deepcopy(dict(protected_target)),
        "source_action_id": source_action_id,
        "source_move_id": move_id,
        "source_terminal_leaf_id": source_terminal_leaf_id,
        "canonical_lifecycle": deepcopy(dict(lifecycle)),
        "active_protection_effect": deepcopy(dict(active_protection_effect)),
        "protection_action_authority": deepcopy(dict(protection_action_authority)),
        "protection_context_fingerprint": protection_context_fingerprint,
        "protection_action_id": _protection_action_id(protection_action_authority),
        "protection_move_id": protection_move_id,
        "protection_family": canonical["family"],
        "canonical_breaks_protect": True,
        "outcome": "bypasses_and_breaks",
        "protection_state_before": "active",
        "protection_state_after": "retired",
        "timing": "after_accuracy_before_hit_resolution",
        "blocked_contact_reactive_consequences_apply": False,
        "ordinary_post_hit_contact_reactions_remain_eligible": True,
        "provenance": "authenticated_vanished_terminal_protection_bypass_break_v1",
    }


def execute_vanished_terminal_through_protection(
    *,
    execution_contract: Mapping[str, Any],
    active_protection_effect: Mapping[str, Any],
    protection_action_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute one authenticated Phantom/Shadow terminal through protection.

    Protect/Detect/reactive shields are bypassed before they can prevent the
    move.  Canonical break retirement occurs only after an accuracy-successful
    hit candidate reaches the break-protection step.
    """
    from llm.advisor_standard_charge_terminal_execution import (
        execute_standard_charge_terminal_attack,
        validate_standard_charge_terminal_execution_contract,
    )
    if validate_standard_charge_terminal_execution_contract(execution_contract) is not None:
        return _result("rejected", "vanished_terminal_execution_contract_invalid")
    move_id = execution_contract.get("move_id")
    if move_id not in _SUPPORTED_MOVES:
        return _result("rejected", "vanished_terminal_move_invalid")
    caller = execution_contract.get("caller_action_authority")
    semi = execution_contract.get("semi_invulnerable_charge_state_authority")
    source_runtime = caller.get("source_runtime_fingerprint") if isinstance(caller, Mapping) else None
    source_branch = caller.get("source_branch_fingerprint") if isinstance(caller, Mapping) else None
    if not isinstance(source_runtime, str) and isinstance(semi, Mapping):
        source_runtime = semi.get("source_runtime_fingerprint")
    if not isinstance(source_branch, str) and isinstance(semi, Mapping):
        source_branch = semi.get("source_branch_fingerprint")
    if not isinstance(source_runtime, str) or not source_runtime or not isinstance(source_branch, str) or not source_branch:
        return _result("rejected", "vanished_terminal_source_fingerprint_unavailable")

    base = execute_standard_charge_terminal_attack(execution_contract=execution_contract)
    if base.get("status") != "resolved":
        return deepcopy(dict(base))
    leaves = base.get("terminal_leaves")
    if not isinstance(leaves, tuple):
        return _result("rejected", "vanished_terminal_ledger_invalid")
    rows = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return _result("rejected", "vanished_terminal_leaf_invalid")
        if leaf.get("hit_state") != "hit":
            rows.append(deepcopy(dict(leaf)))
            continue
        authority = materialize_vanished_protection_bypass_break_authority(
            session_id=execution_contract["session_id"],
            source_runtime_fingerprint=source_runtime,
            source_branch_fingerprint=source_branch,
            decision_owner=execution_contract["decision_owner"],
            attacker=execution_contract["actor"],
            protected_target=execution_contract["target"],
            source_action_id=execution_contract["action_id"],
            move_id=move_id,
            source_terminal_leaf_id=str(leaf.get("leaf_id")),
            active_protection_effect=active_protection_effect,
            protection_action_authority=protection_action_authority,
            protection_context_fingerprint=execution_contract["source_state_fingerprint"],
        )
        if authority.get("status") != "resolved":
            return authority
        attached = attach_vanished_protection_bypass_to_terminal_leaf(
            terminal_leaf=leaf, authority=authority,
        )
        if attached.get("status") in {"incomplete", "unsupported", "rejected"}:
            return attached
        rows.append(attached)
    result = deepcopy(dict(base))
    result["terminal_leaves"] = tuple(rows)
    result["active_protection_effect"] = deepcopy(dict(active_protection_effect))
    result["protection_handling"] = "canonical_breaks_protect_after_accuracy"
    result["provenance"] = "authenticated_vanished_terminal_through_protection_v1"
    return result


def validate_vanished_protection_bypass_break_authority(
    authority: Any,
    *,
    active_protection_effect: Mapping[str, Any] | None = None,
) -> str | None:
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION or authority.get("status") != "resolved":
        return "vanished_protection_bypass_authority_invalid"
    expected = materialize_vanished_protection_bypass_break_authority(
        session_id=authority.get("session_id"),
        source_runtime_fingerprint=authority.get("source_runtime_fingerprint"),
        source_branch_fingerprint=authority.get("source_branch_fingerprint"),
        decision_owner=authority.get("decision_owner"),
        attacker=authority.get("attacker"),
        protected_target=authority.get("protected_target"),
        source_action_id=authority.get("source_action_id"),
        move_id=authority.get("source_move_id"),
        source_terminal_leaf_id=authority.get("source_terminal_leaf_id"),
        active_protection_effect=active_protection_effect or authority.get("active_protection_effect"),
        protection_action_authority=authority.get("protection_action_authority"),
        protection_context_fingerprint=authority.get("protection_context_fingerprint"),
    )
    if expected != dict(authority):
        return "vanished_protection_bypass_authority_mismatch"
    return None


def attach_vanished_protection_bypass_to_terminal_leaf(
    *,
    terminal_leaf: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    if validate_vanished_protection_bypass_break_authority(authority) is not None:
        return _result("rejected", "vanished_protection_bypass_authority_invalid")
    if terminal_leaf.get("leaf_id") != authority.get("source_terminal_leaf_id"):
        return _result("rejected", "vanished_protection_terminal_leaf_mismatch")
    row = deepcopy(dict(terminal_leaf))
    consequences = deepcopy(dict(row.get("consequences", {})))
    consequences["vanished_protection_bypass_break"] = deepcopy(dict(authority))
    consequences["protection_state_transition"] = {
        "owner": deepcopy(authority["protected_target"]),
        "move_id": authority["protection_move_id"],
        "state_before": "active",
        "state_after": "retired",
        "reason": "broken_by_vanished_terminal_attack",
    }
    row["consequences"] = consequences
    provenance = deepcopy(dict(row.get("provenance", {})))
    provenance["vanished_protection_bypass_break_authority"] = deepcopy(dict(authority))
    row["provenance"] = provenance
    return row


def _protection_action_id(value: Mapping[str, Any]) -> str | None:
    action_id = value.get("action_id") if isinstance(value, Mapping) else None
    return action_id if isinstance(action_id, str) and action_id else None


def _protection_action_error(value: Any, protected_target: Mapping[str, Any], attacker: Mapping[str, Any], move_id: Any, context_fingerprint: str) -> str | None:
    if not isinstance(value, Mapping):
        return "vanished_protection_action_authority_missing"
    action_id = _protection_action_id(value)
    action_move = value.get("move_id") or value.get("identity")
    actor = value.get("opponent_actor") or value.get("actor")
    target = value.get("target_owner") or value.get("target")
    fingerprint = value.get("source_branch_fingerprint") or value.get("source_next_decision_fingerprint")
    if action_id is None or action_move != move_id:
        return "vanished_protection_action_identity_mismatch"
    if actor != protected_target or target != attacker:
        return "vanished_protection_action_owner_mismatch"
    if fingerprint != context_fingerprint:
        return "vanished_protection_action_branch_mismatch"
    return None


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and set(value) == _OWNER_KEYS
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
