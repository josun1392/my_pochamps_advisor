"""Explicit, non-recursive two-turn composition for detached Turn Engine branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_end_of_turn_preview import project_poison_end_of_turn
from llm.advisor_next_turn_handoff import handoff_end_of_turn_to_next_turn_start
from llm.advisor_transition_preview import (
    fingerprint_transition_preview_state,
    project_exact_direct_damage_branch,
    project_self_poison_then_direct_branch,
    project_self_recovery_direct_branch,
    project_self_stage_then_direct_branch,
)


def execute_explicit_two_turn(
    *,
    starting_turn_snapshot: Mapping[str, Any],
    turn_one: Mapping[str, Any],
    turn_two: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute exactly two caller-selected action pairs through existing primitives.

    Plans supply existing canonical candidate/order/evaluation evidence.  This
    function neither selects actions nor calculates alternate branches.
    """
    start_fp = fingerprint_transition_preview_state(starting_turn_snapshot)
    if start_fp is None:
        return _result("rejected", "invalid_starting_turn_snapshot")
    first = _execute_turn(turn_snapshot=starting_turn_snapshot, plan=turn_one)
    if first.get("status") != "resolved":
        return _halt(first, "turn_one_transition")
    first_eot = project_poison_end_of_turn(pre_end_of_turn=first)
    if first_eot.get("status") != "resolved":
        return _halt(first_eot, "turn_one_end_of_turn", turn_one=first)
    handoff = handoff_end_of_turn_to_next_turn_start(end_of_turn_branch=first_eot)
    if handoff.get("status") != "resolved":
        return _halt(handoff, "turn_one_handoff", turn_one=first, turn_one_end_of_turn=first_eot)
    if handoff["lifecycle_trace"][0]["requires_replacement_before_action"]:
        return _halt({"status": "unsupported", "reason": "replacement_required_before_turn_two"}, "turn_two_replacement", turn_one=first, turn_one_end_of_turn=first_eot, next_turn_start=handoff)

    next_fp = handoff["resulting_branch_fingerprint"]
    if turn_two.get("start_branch_fingerprint") != next_fp:
        return _halt({"status": "rejected", "reason": "turn_two_branch_fingerprint_mismatch"}, "turn_two_ownership", turn_one=first, turn_one_end_of_turn=first_eot, next_turn_start=handoff)
    owners = _owners(handoff["next_state"])
    if owners is None or not _plan_owners_match(turn_two, owners):
        return _halt({"status": "rejected", "reason": "stale_or_mismatched_turn_two_action_owner"}, "turn_two_ownership", turn_one=first, turn_one_end_of_turn=first_eot, next_turn_start=handoff)
    second_snapshot = _snapshot_from_next_turn_start(handoff)
    if second_snapshot is None:
        return _halt({"status": "rejected", "reason": "invalid_next_turn_start_state"}, "turn_two_snapshot", turn_one=first, turn_one_end_of_turn=first_eot, next_turn_start=handoff)
    second = _execute_turn(turn_snapshot=second_snapshot, plan=turn_two)
    if second.get("status") != "resolved":
        return _halt(second, "turn_two_transition", turn_one=first, turn_one_end_of_turn=first_eot, next_turn_start=handoff)
    second_eot = project_poison_end_of_turn(pre_end_of_turn=second)
    if second_eot.get("status") != "resolved":
        return _halt(second_eot, "turn_two_end_of_turn", turn_one=first, turn_one_end_of_turn=first_eot, next_turn_start=handoff, turn_two=second)
    return {
        "status": "resolved",
        "source_snapshot_fingerprint": start_fp,
        "turn_one": deepcopy(first),
        "turn_one_end_of_turn": deepcopy(first_eot),
        "next_turn_start": deepcopy(handoff),
        "turn_two": deepcopy(second),
        "turn_two_end_of_turn": deepcopy(second_eot),
        "resulting_branch_fingerprint": second_eot["resulting_branch_fingerprint"],
        "boundary": {"phase": "end_of_turn", "turn": 2},
        "limitations": ["two_explicit_turns_only", "no_action_selection_or_branch_search", "no_third_turn_or_recursion"],
    }


def _execute_turn(*, turn_snapshot: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        return _result("rejected", "invalid_turn_plan")
    common = {key: plan.get(key) for key in ("self_action", "opponent_action", "self_candidate", "opponent_candidate", "action_order")}
    kind = plan.get("transition", "exact_direct")
    if kind == "exact_direct":
        return project_exact_direct_damage_branch(turn_snapshot=turn_snapshot, **common, post_first_candidate=plan.get("post_first_candidate"), second_direct_evaluation_input=plan.get("second_direct_evaluation_input"))
    if kind == "self_stage_then_direct":
        return project_self_stage_then_direct_branch(turn_snapshot=turn_snapshot, **common, second_direct_evaluation_input=plan.get("second_direct_evaluation_input"))
    if kind == "self_recovery_then_direct":
        return project_self_recovery_direct_branch(turn_snapshot=turn_snapshot, **common, opponent_direct_evaluation_input=plan.get("opponent_direct_evaluation_input"))
    if kind == "self_poison_then_direct":
        return project_self_poison_then_direct_branch(turn_snapshot=turn_snapshot, **common, second_direct_evaluation_input=plan.get("second_direct_evaluation_input"))
    return _result("unsupported", "turn_transition_not_in_slice")


def _snapshot_from_next_turn_start(handoff: Mapping[str, Any]) -> dict[str, Any] | None:
    state = handoff.get("next_state")
    owners = _owners(state) if isinstance(state, Mapping) else None
    if owners is None or not isinstance(state.get("current_state"), Mapping):
        return None
    current = deepcopy(dict(state["current_state"]))
    if current.get("current_state_session_id") != owners["self"]["session_id"]:
        return None
    snapshot = {
        "battle_state": {
            "active_player": {"slot_index": owners["self"]["slot_index"], "species_id": owners["self"]["pokemon_id"]},
            "active_opponent": {"slot_index": owners["opponent"]["slot_index"], "species_id": owners["opponent"]["pokemon_id"]},
        },
        "current_state": current,
    }
    overlays = {key: deepcopy(state[key]) for key in ("predicted_stage_context", "predicted_condition_context", "predicted_toxic_lifecycle") if key in state}
    if overlays:
        snapshot["turn_engine_branch_overlays"] = overlays
    return snapshot


def _owners(state: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    active = state.get("active") if isinstance(state, Mapping) else None
    if not isinstance(active, Mapping):
        return None
    owners: dict[str, dict[str, Any]] = {}
    for side in ("self", "opponent"):
        row = active.get(side)
        if not isinstance(row, Mapping) or row.get("side") != side:
            return None
        owner = {key: row.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")}
        if not isinstance(owner["session_id"], str) or not owner["session_id"] or not isinstance(owner["slot_index"], int) or isinstance(owner["slot_index"], bool) or not isinstance(owner["pokemon_id"], str) or not owner["pokemon_id"]:
            return None
        owners[side] = owner
    return owners if owners["self"]["session_id"] == owners["opponent"]["session_id"] else None


def _plan_owners_match(plan: Mapping[str, Any], owners: Mapping[str, Mapping[str, Any]]) -> bool:
    for side in ("self", "opponent"):
        action = plan.get(f"{side}_action")
        if not isinstance(action, Mapping) or action.get("owner") != owners[side]:
            return False
    return True


def _halt(result: Mapping[str, Any], stage: str, **completed: Any) -> dict[str, Any]:
    return {"status": result.get("status", "incomplete"), "reason": result.get("reason", stage), "failed_stage": stage, **{key: deepcopy(value) for key, value in completed.items()}}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
