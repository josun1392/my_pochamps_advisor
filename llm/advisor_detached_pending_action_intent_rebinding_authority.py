"""Bridge immutable selected intent to one exact detached execution branch."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "detached-pending-action-intent-rebinding-authority-v1"
_OWNER = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_pending_action_intent_rebinding_authority(*, original_strategy_d0: Mapping[str, Any], action: Mapping[str, Any], move_metadata_authority: Mapping[str, Any], replacement_authority: Mapping[str, Any], intermediate_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Prove that an already selected action may execute from a new branch.

    This intentionally records both fingerprints; it never rewrites the
    decision-time authority to pretend it originated on the new branch.
    """
    original = _original(original_strategy_d0, action, move_metadata_authority, replacement_authority)
    if isinstance(original, str): return _result("incomplete" if original.startswith("missing_") else "rejected", original)
    branch = _branch(intermediate_authority, original)
    if isinstance(branch, str): return _result("incomplete" if branch.startswith("missing_") else "rejected", branch)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "session_id": original["session_id"],
        "source_decision_fingerprint": original["source_branch_fingerprint"],
        "decision_owner": deepcopy(original["decision_owner"]),
        "action_id": original["action_id"], "move_id": original["move_id"],
        "move_metadata": deepcopy(original["move_metadata"]),
        "selected_replacement_owner": deepcopy(original["replacement_owner"]),
        "original_intent": deepcopy(original),
        "source_first_action_leaf_id": branch["source_first_action_leaf_id"],
        "source_branch_fingerprint": branch["source_branch_fingerprint"],
        "predictive_runtime_fingerprint": branch["predictive_runtime_fingerprint"],
        "current_actor": deepcopy(branch["actor"]), "current_target": deepcopy(branch["target"]),
        "predictive_strategy_d0": deepcopy(branch["predictive_strategy_d0"]),
        "predictive_runtime_snapshot": deepcopy(branch["predictive_runtime_snapshot"]),
        "provenance": "original_selected_intent_to_exact_intermediate_branch_v1",
    }


def _original(d0: Any, action: Any, metadata_authority: Any, replacement: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved": return "original_d0_invalid"
    owner = d0.get("decision_owner")
    if not _owner(owner): return "original_decision_owner_invalid"
    base = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(dict(owner))}
    if not all(isinstance(base[k], str) and base[k] for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")): return "original_d0_invalid"
    if not isinstance(action, Mapping) or not isinstance(action.get("action_id"), str): return "missing_action_evidence"
    meta = metadata_authority.get("metadata") if isinstance(metadata_authority, Mapping) else None
    if not isinstance(meta, Mapping) or not isinstance(meta.get("move_id"), str): return "missing_move_metadata_evidence"
    if action["action_id"] != f"attack:{meta['move_id']}": return "action_move_identity_mismatch"
    expected = {**base, "move_id": meta["move_id"]}
    if metadata_authority.get("status") != "resolved" or any(metadata_authority.get(k) != v for k, v in expected.items()): return "original_move_metadata_binding_mismatch"
    if not isinstance(replacement, Mapping): return "missing_replacement_evidence"
    repl_owner = replacement.get("owner")
    if replacement.get("status") != "resolved" or not _owner(repl_owner) or repl_owner["side"] != "self" or repl_owner == owner or any(replacement.get(k) != v for k, v in base.items()): return "original_replacement_binding_mismatch"
    return {**base, "action_id": action["action_id"], "move_id": meta["move_id"], "move_metadata": deepcopy(dict(meta)), "replacement_owner": deepcopy(dict(repl_owner))}


def _branch(value: Any, original: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != "detached-intermediate-predictive-authority-v1": return "intermediate_authority_invalid"
    actor, target, d0, snapshot = value.get("predictive_actor"), value.get("predictive_target"), value.get("predictive_strategy_d0"), value.get("predictive_runtime_snapshot")
    if not _owner(actor) or not _owner(target) or actor != original["decision_owner"]: return "pending_actor_identity_mismatch"
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or d0.get("decision_owner") != actor or d0.get("active_owners", {}).get("self") != actor: return "pending_actor_not_active"
    if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("state_fingerprint"), str): return "missing_branch_runtime_fingerprint"
    if value.get("session_id") != original["session_id"] or d0.get("session_id") != original["session_id"]: return "foreign_session"
    if not isinstance(value.get("source_first_action_leaf_id"), str) or not isinstance(d0.get("strategy_preview_fingerprint"), str): return "missing_branch_evidence"
    return {"source_first_action_leaf_id": value["source_first_action_leaf_id"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "predictive_runtime_fingerprint": snapshot["state_fingerprint"], "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "predictive_strategy_d0": deepcopy(dict(d0)), "predictive_runtime_snapshot": deepcopy(dict(snapshot))}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and isinstance(value.get("pokemon_id"), str)
def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
