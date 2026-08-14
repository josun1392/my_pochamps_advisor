"""Branch-bound adapter for the existing native direct-mechanics evaluator."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_opponent_action_evaluator import _side_reversed_current_state
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_hypothetical_stage_effects import overlay_predicted_stage_for_direct_mechanics
from llm.advisor_hypothetical_condition_effects import overlay_predicted_condition_for_direct_mechanics


def evaluate_hypothetical_direct_mechanics(
    *,
    branch_state: Mapping[str, Any],
    source_snapshot_fingerprint: str,
    action: Mapping[str, Any],
    expected_owner: Mapping[str, Any],
    direct_evaluation_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one owned direct action against detached branch authority only.

    ``direct_evaluation_input`` is a frozen, action-oriented descriptor made
    from the existing snapshot/direct-mechanics boundary.  It contains no
    runtime handle and supplies only canonical move metadata, stat provenance,
    and trusted level.  The mutable-looking working input below is a deep copy
    owned exclusively by this pure call.
    """
    branch_fingerprint = fingerprint_transition_preview_state(branch_state)
    if branch_fingerprint is None or not _valid_branch(branch_state):
        return _result("rejected", "invalid_branch_state", branch_fingerprint)
    if not _same_owner(action.get("owner"), expected_owner):
        return _result("rejected", "stale_or_mismatched_action_owner", branch_fingerprint)
    move = action.get("move")
    if not isinstance(move, Mapping) or move.get("category") not in {"physical", "special"}:
        return _result("unsupported_mechanic", "action_not_direct_damage", branch_fingerprint)
    if not isinstance(direct_evaluation_input, Mapping):
        return _result("rejected", "invalid_direct_evaluation_input", branch_fingerprint)
    if direct_evaluation_input.get("source_snapshot_fingerprint") != source_snapshot_fingerprint:
        return _result("rejected", "source_snapshot_fingerprint_mismatch", branch_fingerprint)
    if not _same_owner(direct_evaluation_input.get("owner"), expected_owner):
        return _result("rejected", "direct_evaluation_owner_mismatch", branch_fingerprint)
    if direct_evaluation_input.get("branch_state_fingerprint") not in {None, branch_fingerprint}:
        return _result("rejected", "direct_evaluation_branch_mismatch", branch_fingerprint)
    descriptor_move = direct_evaluation_input.get("move_metadata")
    if not _same_move(descriptor_move, move):
        return _result("rejected", "direct_evaluation_move_mismatch", branch_fingerprint)
    provenance, trusted_level = direct_evaluation_input.get("stat_provenance"), direct_evaluation_input.get("trusted_level")
    if not isinstance(provenance, Mapping):
        return _result("incomplete", "stat_provenance", branch_fingerprint, missing_inputs=["stat_provenance"])
    if isinstance(trusted_level, bool) or not isinstance(trusted_level, int) or not 1 <= trusted_level <= 100:
        return _result("incomplete", "attacker.level", branch_fingerprint, missing_inputs=["attacker.level"])

    current = branch_state.get("current_state")
    if not isinstance(current, Mapping):
        return _result("rejected", "branch_current_state", branch_fingerprint)
    calculator_current = overlay_predicted_stage_for_direct_mechanics(current, branch_state.get("predicted_stage_context"))
    if calculator_current is None:
        return _result("incomplete", "predicted_stage_authority", branch_fingerprint, missing_inputs=["predicted_stage_authority"])
    predicted_condition = branch_state.get("predicted_condition_context")
    if isinstance(predicted_condition, Mapping):
        base_branch = deepcopy(dict(branch_state)); base_branch.pop("predicted_condition_context", None); base_branch.pop("predicted_toxic_lifecycle", None)
        if predicted_condition.get("branch_state_fingerprint") != fingerprint_transition_preview_state(base_branch):
            return _result("rejected", "predicted_condition_branch_mismatch", branch_fingerprint)
    calculator_current = overlay_predicted_condition_for_direct_mechanics(calculator_current, predicted_condition)
    if calculator_current is None:
        return _result("incomplete", "predicted_condition_authority", branch_fingerprint, missing_inputs=["predicted_condition_authority"])
    oriented_current = calculator_current if expected_owner.get("side") == "self" else _side_reversed_current_state(calculator_current)
    damage_input = {
        "move": deepcopy(dict(descriptor_move)),
        "battle_context": {"current_state": oriented_current},
    }
    mechanics = evaluate_direct_damage_mechanics(
        damage_input,
        stat_provenance=deepcopy(dict(provenance)),
        trusted_level=trusted_level,
    )
    status = mechanics.get("status") if isinstance(mechanics, Mapping) else "insufficient_context"
    if status not in {"known", "insufficient_context", "unsupported_mechanic"}:
        return _result("incomplete", "native_direct_mechanics", branch_fingerprint)
    return {
        "status": status,
        "reason": mechanics.get("unsupported_reason") if status == "unsupported_mechanic" else "native_direct_mechanics",
        "branch_state_fingerprint": branch_fingerprint,
        "source_snapshot_fingerprint": source_snapshot_fingerprint,
        "owner": deepcopy(dict(expected_owner)),
        "move": deepcopy(dict(move)),
        "mechanics_result": deepcopy(dict(mechanics)),
        **({"missing_inputs": deepcopy(mechanics.get("missing_inputs", []))} if status == "insufficient_context" else {}),
    }


def _valid_branch(value: Mapping[str, Any]) -> bool:
    active = value.get("active")
    current = value.get("current_state")
    if value.get("schema_version") != "deterministic-transition-preview-v1" or not isinstance(active, Mapping) or not isinstance(current, Mapping):
        return False
    for side in ("self", "opponent"):
        entry = active.get(side)
        if not isinstance(entry, Mapping) or entry.get("side") != side or not isinstance(entry.get("session_id"), str) or not entry["session_id"]:
            return False
        if isinstance(entry.get("slot_index"), bool) or not isinstance(entry.get("slot_index"), int) or entry["slot_index"] < 0 or not isinstance(entry.get("pokemon_id"), str) or not entry["pokemon_id"]:
            return False
        hp, maximum = entry.get("current_hp"), entry.get("max_hp")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in (hp, maximum)) or maximum < 1 or hp < 0 or hp > maximum or entry.get("fainted") is not (hp == 0):
            return False
    return True


def _same_owner(value: Any, expected: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and all(value.get(key) == expected.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id"))


def _same_move(value: Any, action_move: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and value.get("move_id") == action_move.get("move_id") and value.get("slot_index") == action_move.get("slot_index") and value.get("category") == action_move.get("category")


def _result(status: str, reason: str, branch_fingerprint: str | None, *, missing_inputs: list[str] | None = None) -> dict[str, Any]:
    result = {"status": status, "reason": reason, "branch_state_fingerprint": branch_fingerprint, "mechanics_result": None}
    if missing_inputs is not None:
        result["missing_inputs"] = deepcopy(missing_inputs)
    return result
