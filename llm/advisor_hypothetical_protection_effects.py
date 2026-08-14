"""Checked-in ordinary Protect authority for detached Turn Engine branches."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

_PATH = Path(__file__).parents[1] / "data" / "static" / "protection_move_effects.json"


def canonical_protection_metadata(move_id: Any) -> dict[str, Any] | None:
    if not isinstance(move_id, str) or not move_id:
        return None
    data = json.loads(_PATH.read_text(encoding="utf-8"))
    row = data.get("moves", {}).get(move_id)
    if not isinstance(row, Mapping):
        return None
    required = ("protects_self", "blocks_supported_direct_damage", "protection_kind", "has_additional_material_effects")
    if any(key not in row for key in required) or row.get("protects_self") is not True or row.get("blocks_supported_direct_damage") is not True or row.get("has_additional_material_effects") is not False or row.get("protection_kind") != "ordinary_self_protection":
        return None
    return {"move_id": move_id, **deepcopy(dict(row))}


def project_self_protection(*, branch_state: Mapping[str, Any], action: Mapping[str, Any], expected_owner: Mapping[str, Any], success_authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(branch_state, Mapping) or branch_state.get("schema_version") != "deterministic-transition-preview-v1":
        return _result("rejected", "invalid_branch_state")
    owner = action.get("owner") if isinstance(action, Mapping) else None
    active = branch_state.get("active", {}).get("self") if isinstance(branch_state.get("active"), Mapping) else None
    if not _same(owner, expected_owner) or not _same(active, expected_owner):
        return _result("rejected", "stale_or_mismatched_protection_owner")
    if active.get("fainted") is not False:
        return _result("incomplete", "protection_actor_execution_state")
    move = action.get("move")
    metadata = canonical_protection_metadata(move.get("move_id") if isinstance(move, Mapping) else None)
    if not isinstance(move, Mapping) or move.get("category") != "status" or move.get("target") != "user" or metadata is None:
        return _result("unsupported", "canonical_protection_metadata")
    if move.get("accuracy") is not None:
        return _result("incomplete", "protection_move_success_uncertain")
    if not _valid_success(success_authority, expected_owner):
        return _result("incomplete", "protection_chain_authority")
    return {"status": "resolved", "owner": deepcopy(dict(expected_owner)), "metadata": metadata, "provenance": "turn_engine_explicit_nonconsecutive_protection_v1"}


def prevent_supported_direct_damage(*, effect: Mapping[str, Any], opponent_action: Mapping[str, Any], protected_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Authorize no HP mutation for one explicitly non-bypassing direct action."""
    move = opponent_action.get("move") if isinstance(opponent_action, Mapping) else None
    if not isinstance(effect, Mapping) or effect.get("status") != "resolved" or not _same(effect.get("owner"), protected_owner):
        return _result("rejected", "stale_or_mismatched_protection_effect")
    if not isinstance(move, Mapping) or move.get("category") not in {"physical", "special"}:
        return _result("unsupported", "protection_opponent_action_not_direct_damage")
    if move.get("protection_bypass") is not False:
        return _result("incomplete", "protection_bypass_authority")
    return {"status": "resolved", "owner": deepcopy(dict(protected_owner)), "execution_status": "prevented", "reason": "ordinary_self_protection_blocks_supported_direct_damage"}


def project_protection_direct_transition(*, branch_state: Mapping[str, Any], self_action: Mapping[str, Any], opponent_action: Mapping[str, Any], owner: Mapping[str, Any], success_authority: Mapping[str, Any], action_order: Mapping[str, Any]) -> dict[str, Any]:
    """Small detached pre-EOT adapter; prevention never applies or restores damage."""
    if not isinstance(action_order, Mapping) or action_order.get("status") != "acts_first":
        return _result("incomplete", "protection_action_order")
    effect = project_self_protection(branch_state=branch_state, action=self_action, expected_owner=owner, success_authority=success_authority)
    if effect.get("status") != "resolved": return effect
    prevented = prevent_supported_direct_damage(effect=effect, opponent_action=opponent_action, protected_owner=owner)
    if prevented.get("status") != "resolved": return prevented
    state = deepcopy(dict(branch_state)); state["predicted_protection_context"] = {"schema_version": "hypothetical-ordinary-protection-v1", "owner": deepcopy(dict(owner)), "provenance": effect["provenance"], "expires_at": "end_of_turn"}
    return {"status": "resolved", "next_state": state, "protection_effect": effect, "consequence_trace": [{"sequence": 1, "execution_status": "executed", "consequence": "ordinary_self_protection"}, {"sequence": 2, "execution_status": "prevented", "reason": prevented["reason"]}], "boundary": {"phase": "pre_end_of_turn"}}


def _valid_success(value: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("schema_version") == "branch-protection-success-v1" and value.get("owner") == owner and value.get("previous_successful_protection_count") == 0 and value.get("provenance") == "explicit_branch_nonconsecutive_protection"


def _same(a: Any, b: Any) -> bool:
    return isinstance(a, Mapping) and isinstance(b, Mapping) and all(a.get(k) == b.get(k) for k in ("session_id", "side", "slot_index", "pokemon_id"))


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "reason": reason}
