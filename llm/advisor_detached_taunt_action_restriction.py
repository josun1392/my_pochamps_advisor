"""Detached Taunt application and execution restriction mechanics."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

SCHEMA_VERSION = "detached-taunt-action-restriction-v1"
_BINDING = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")


def materialize_detached_taunt_application(*, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], accuracy_authority: Mapping[str, Any], target_ability_authority: Mapping[str, Any], target_side_ability_authority: Mapping[str, Any], protection_authority: Mapping[str, Any] | None = None, reflection_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None: return _result("rejected", "taunt_application_binding_invalid", {})
    for value, label in ((accuracy_authority, "accuracy"), (target_ability_authority, "target_ability"), (target_side_ability_authority, "target_side_ability")):
        bad = _bound_known(value, base, label)
        if bad: return _result(bad[0], bad[1], base)
    if protection_authority is not None:
        bad = _bound_known(protection_authority, base, "protection")
        if bad: return _result(bad[0], bad[1], base)
        if protection_authority.get("outcome") == "blocked": return _outcome(base, "blocked", "taunt_blocked_by_protection", protection_authority)
        if protection_authority.get("outcome") != "not_applicable": return _result("rejected", "taunt_protection_outcome_invalid", base)
    if reflection_authority is None: return _result("incomplete", "taunt_reflection_authority_missing", base)
    bad = _bound_known(reflection_authority, base, "reflection")
    if bad: return _result(bad[0], bad[1], base)
    if reflection_authority.get("outcome") == "reflected": return _result("incomplete", "taunt_reflection_execution_unsupported", base)
    if reflection_authority.get("outcome") != "not_applicable": return _result("rejected", "taunt_reflection_outcome_invalid", base)
    if target_ability_authority.get("ability") == "oblivious": return _outcome(base, "no_effect", "taunt_target_oblivious", target_ability_authority)
    if target_side_ability_authority.get("ability") == "aroma-veil": return _outcome(base, "no_effect", "taunt_target_protected_by_aroma_veil", target_side_ability_authority)
    if accuracy_authority.get("outcome") == "missed": return _outcome(base, "missed", "taunt_missed", accuracy_authority)
    if accuracy_authority.get("outcome") != "hit": return _result("rejected", "taunt_accuracy_outcome_invalid", base)
    return _outcome(base, "applied", "taunt_applied", accuracy_authority, remaining_target_turns=3)


def materialize_taunt_execution_gate(*, selected_action: Mapping[str, Any], actor: Mapping[str, Any], current_restriction: Mapping[str, Any] | None = None, same_branch_application: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Gate an already selected action without rewriting its selected intent."""
    meta = selected_action.get("metadata_authority", selected_action.get("move_metadata_authority")) if isinstance(selected_action, Mapping) else None
    metadata = meta.get("metadata") if isinstance(meta, Mapping) else None
    if not isinstance(metadata, Mapping) or metadata.get("category") not in {"physical", "special", "status"}: return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "selected_action_move_category_unknown"}
    sources = [x for x in (current_restriction, same_branch_application) if x is not None]
    if not sources: return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "taunt_restriction_authority_missing"}
    active = False
    evidence = []
    for source in sources:
        if not isinstance(source, Mapping): return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "taunt_restriction_authority_invalid"}
        if source.get("owner", source.get("target")) != dict(actor): return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "taunt_restriction_actor_binding_mismatch"}
        if source.get("status") == "resolved" and source.get("outcome") == "applied": active = True
        elif source.get("status") == "resolved": active |= source.get("state") == "active"
        elif source.get("status") in {"incomplete", "rejected"}: return {"status": source["status"], "schema_version": SCHEMA_VERSION, "reason": source.get("reason", "taunt_restriction_unavailable")}
        evidence.append(deepcopy(dict(source)))
    restricted = active and metadata["category"] == "status"
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "actor": deepcopy(dict(actor)), "selected_action_id": selected_action.get("action_id"), "selected_move_id": metadata.get("move_id"), "selected_move_category": metadata["category"], "execution_state": "restricted_by_taunt" if restricted else "executable", "reason": "taunt_restricts_selected_status_action" if restricted else "taunt_does_not_restrict_selected_damaging_action", "restriction_evidence": tuple(evidence), "provenance": "selected_intent_preserved_taunt_execution_gate_v1"}


def taunt_restriction_failure_leaf(*, strategy_d0: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], gate: Mapping[str, Any]) -> dict[str, Any]:
    active = strategy_d0.get("strategy_state", {}).get("active", {})
    own_hp, target_hp = active.get(actor.get("side"), {}).get("current_hp"), active.get(target.get("side"), {}).get("current_hp")
    if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (own_hp, target_hp)): return _result("incomplete", "taunt_failure_hp_authority_missing", {})
    if gate.get("status") != "resolved" or gate.get("execution_state") != "restricted_by_taunt": return _result("rejected", "taunt_failure_gate_invalid", {})
    leaf = {"leaf_id": f"{action['action_id']}:taunt_restricted", "candidate_id": action["action_id"], "action_type": action.get("action_type", "attack"), "branch_path": ("action_restriction", "taunt"), "probability": {"numerator": 1, "denominator": 1}, "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "consequences": {"damage": 0, "own_final_hp": own_hp, "target_final_hp": target_hp, "target_ko": target_hp == 0, "self_fainted": own_hp == 0, "secondary": None, "contact": "not_applicable", "execution_failure": "taunt_action_restriction", "taunt_execution_gate": deepcopy(dict(gate))}, "provenance": {**_binding(strategy_d0), "attacker": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "move_id": gate.get("selected_move_id"), "taunt_action_restriction": deepcopy(dict(gate))}}
    return {"status": "evaluable", "terminal_leaves": (leaf,), "terminal_probability_mass": {"numerator": 1, "denominator": 1}}


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(actor, Mapping) or not isinstance(target, Mapping): return None
    meta = action.get("metadata_authority", action.get("move_metadata_authority")); metadata = meta.get("metadata") if isinstance(meta, Mapping) else None
    if d0.get("active_owners", {}).get(actor.get("side")) != dict(actor) or d0.get("active_owners", {}).get(target.get("side")) != dict(target) or not isinstance(metadata, Mapping) or metadata.get("move_id") != "taunt" or metadata.get("category") != "status": return None
    return {**_binding(d0), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action.get("action_id"), "move_id": "taunt"}

def _binding(d0: Mapping[str, Any]) -> dict[str, Any]: return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"]))}
def _bound_known(value: Any, base: Mapping[str, Any], label: str) -> tuple[str, str] | None:
    if not isinstance(value, Mapping): return ("incomplete", f"taunt_{label}_authority_missing")
    if value.get("status") != "resolved": return (value.get("status") if value.get("status") in {"incomplete", "rejected"} else "rejected", value.get("reason", f"taunt_{label}_authority_unavailable"))
    if any(value.get(key) != base.get(key) for key in _BINDING): return ("rejected", f"taunt_{label}_authority_binding_mismatch")
    return None
def _outcome(base: Mapping[str, Any], outcome: str, reason: str, authority: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome, "reason": reason, **deepcopy(extra), "authority": deepcopy(dict(authority)), "provenance": "strict_detached_taunt_application_v1"}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
