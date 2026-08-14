"""Pure, fail-closed deterministic transition previews.

This Practical 2.0 slice supports exact direct damage plus narrowly supported
self-action effects.  It is not a reducer, a damage calculator, or a simulator.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping


_DIRECT_CATEGORIES = frozenset({"physical", "special"})
_NATIVE_SOURCES = frozenset({"native_q12_direct_damage", "native_level_based_fixed_damage"})


def project_guaranteed_terminal_direct_ko_branch(
    *,
    turn_snapshot: Any,
    self_action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
    self_candidate: Mapping[str, Any],
    opponent_candidate: Mapping[str, Any],
    action_order: Mapping[str, Any],
) -> dict[str, Any]:
    """Compatibility entry point for the original terminal-only contract."""
    return project_exact_direct_damage_branch(
        turn_snapshot=turn_snapshot,
        self_action=self_action,
        opponent_action=opponent_action,
        self_candidate=self_candidate,
        opponent_candidate=opponent_candidate,
        action_order=action_order,
    )


def project_exact_direct_action_on_branch(
    *, branch_state: Mapping[str, Any], source_snapshot_fingerprint: str, action: Mapping[str, Any], candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply one existing exact direct result to a detached branch.

    This is a thin continuation seam for a prior switch-first action, not a
    second mechanics implementation or an action-order policy.
    """
    state = deepcopy(dict(branch_state)) if isinstance(branch_state, Mapping) else None
    fingerprint = _fingerprint(state) if isinstance(state, Mapping) else None
    if fingerprint is None or not isinstance(state.get("active"), Mapping):
        return _result("rejected", "invalid_branch_state", source_snapshot_fingerprint)
    actor = state["active"].get("opponent")
    target = state["active"].get("self")
    if not isinstance(actor, Mapping) or not isinstance(target, Mapping):
        return _result("rejected", "invalid_branch_ownership", source_snapshot_fingerprint)
    expected = {key: actor.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")}
    reason = _validate_action(action, expected=expected) or _validate_candidate_binding(candidate, action)
    if reason is not None:
        return _result("rejected", reason, source_snapshot_fingerprint)
    outcome = _apply_exact_direct_damage(state=state, actor_side="opponent", target_side="self", action=action, candidate=candidate)
    if outcome["status"] != "resolved":
        return _result(outcome["status"], outcome["reason"], source_snapshot_fingerprint, missing_inputs=outcome.get("missing_inputs"))
    trace = [_executed_trace(sequence=1, actor_side="opponent", action=action, target={key: target[key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, outcome=outcome)]
    return _resolved(source_snapshot_fingerprint, {"self": {key: state["active"]["self"][key] for key in ("session_id", "side", "slot_index", "pokemon_id")}, "opponent": expected}, {"status": "self_switch_first"}, trace, state, "post_switch_terminal_direct_ko" if outcome["terminal"] else "post_switch_exact_direct_damage")


def project_exact_direct_damage_branch(
    *,
    turn_snapshot: Any,
    self_action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
    self_candidate: Mapping[str, Any],
    opponent_candidate: Mapping[str, Any],
    action_order: Mapping[str, Any],
    post_first_candidate: Mapping[str, Any] | None = None,
    second_direct_evaluation_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project up to two exact direct actions from frozen, existing evidence.

    The optional ``post_first_candidate`` must be canonical direct-mechanics
    evidence recomputed for the detached post-first state and carry its exact
    ``branch_state_fingerprint``.  The adapter never reuses the original
    second-action evidence after HP has changed.
    """
    snapshot = _serialize_snapshot(turn_snapshot)
    if snapshot is None:
        return _result("rejected", "invalid_frozen_snapshot")
    fingerprint = _fingerprint(snapshot)
    if fingerprint is None:
        return _result("rejected", "unserializable_frozen_snapshot")
    owners = _snapshot_owners(snapshot)
    if owners is None:
        return _result("rejected", "invalid_snapshot_ownership", fingerprint)

    actions = {"self": self_action, "opponent": opponent_action}
    candidates = {"self": self_candidate, "opponent": opponent_candidate}
    for side in ("self", "opponent"):
        reason = _validate_action(actions[side], expected=owners[side])
        if reason is not None:
            return _result("rejected", reason, fingerprint)
        reason = _validate_candidate_binding(candidates[side], actions[side])
        if reason is not None:
            return _result("rejected", reason, fingerprint)
        if _action_category(actions[side]) not in _DIRECT_CATEGORIES:
            return _result("unsupported", f"{side}_action_not_direct_damage", fingerprint)

    order_status = action_order.get("status") if isinstance(action_order, Mapping) else None
    if order_status == "speed_tie":
        return _result("incomplete", "speed_tie", fingerprint)
    if order_status == "unsupported_mechanic":
        return _result("unsupported", str(action_order.get("unsupported_reason") or "action_order_unsupported"), fingerprint)
    if order_status not in {"acts_first", "acts_second"}:
        missing = action_order.get("missing_inputs") if isinstance(action_order, Mapping) else None
        return _result("incomplete", "action_order", fingerprint, missing_inputs=missing)
    if not _order_matches_actions(action_order, actions):
        return _result("rejected", "action_order_action_mismatch", fingerprint)

    for side in ("self", "opponent"):
        if _trusted_active_hp(snapshot, side) is None:
            return _result("incomplete", f"{side}_exact_hp", fingerprint)
    next_state = _initial_next_state(snapshot, owners)
    first_side = "self" if order_status == "acts_first" else "opponent"
    second_side = "opponent" if first_side == "self" else "self"
    first = _apply_exact_direct_damage(
        state=next_state, actor_side=first_side, target_side=second_side,
        action=actions[first_side], candidate=candidates[first_side],
    )
    if first["status"] != "resolved":
        return _result(first["status"], first["reason"], fingerprint, missing_inputs=first.get("missing_inputs"))
    trace = [_executed_trace(sequence=1, actor_side=first_side, action=actions[first_side], target=owners[second_side], outcome=first)]
    if first["terminal"]:
        trace.append({"sequence": 2, "actor_side": second_side, "action": _public_action(actions[second_side]), "execution_status": "skipped", "reason": "actor_fainted_by_terminal_first_action"})
        return _resolved(fingerprint, owners, action_order, trace, next_state, "guaranteed_terminal_direct_ko")

    if post_first_candidate is not None and second_direct_evaluation_input is not None:
        return _result("rejected", "competing_second_action_evidence", fingerprint)
    if isinstance(second_direct_evaluation_input, Mapping):
        from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
        evaluated = evaluate_hypothetical_direct_mechanics(
            branch_state=next_state,
            source_snapshot_fingerprint=fingerprint,
            action=actions[second_side],
            expected_owner=owners[second_side],
            direct_evaluation_input=second_direct_evaluation_input,
        )
        if evaluated.get("status") != "known":
            status = "unsupported" if evaluated.get("status") == "unsupported_mechanic" else "rejected" if evaluated.get("status") == "rejected" else "incomplete"
            return _result(status, str(evaluated.get("reason") or "post_first_direct_mechanics"), fingerprint, missing_inputs=evaluated.get("missing_inputs"))
        post_first_candidate = {
            "branch_state_fingerprint": evaluated["branch_state_fingerprint"],
            "candidate": {**deepcopy(dict(candidates[second_side])), "mechanics_result": deepcopy(evaluated["mechanics_result"])},
        }
    if not isinstance(post_first_candidate, Mapping):
        return _result("incomplete", "post_first_direct_mechanics_evidence", fingerprint)
    expected_branch = _fingerprint(next_state)
    if post_first_candidate.get("branch_state_fingerprint") != expected_branch:
        return _result("rejected", "post_first_candidate_branch_mismatch", fingerprint)
    second_candidate = post_first_candidate.get("candidate")
    binding = _validate_candidate_binding(second_candidate, actions[second_side])
    if binding is not None:
        return _result("rejected", binding, fingerprint)
    second = _apply_exact_direct_damage(
        state=next_state, actor_side=second_side, target_side=first_side,
        action=actions[second_side], candidate=second_candidate,
    )
    if second["status"] != "resolved":
        return _result(second["status"], second["reason"], fingerprint, missing_inputs=second.get("missing_inputs"))
    trace.append(_executed_trace(sequence=2, actor_side=second_side, action=actions[second_side], target=owners[first_side], outcome=second))
    reason = "two_action_terminal_direct_ko" if second["terminal"] else "two_action_exact_direct_damage"
    return _resolved(fingerprint, owners, action_order, trace, next_state, reason)


def project_self_stage_then_direct_branch(
    *,
    turn_snapshot: Any,
    self_action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
    self_candidate: Mapping[str, Any],
    opponent_candidate: Mapping[str, Any],
    action_order: Mapping[str, Any],
    second_direct_evaluation_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one exact self-stage action followed by one direct opponent move."""
    snapshot = _serialize_snapshot(turn_snapshot)
    if snapshot is None:
        return _result("rejected", "invalid_frozen_snapshot")
    fingerprint = _fingerprint(snapshot)
    if fingerprint is None:
        return _result("rejected", "unserializable_frozen_snapshot")
    owners = _snapshot_owners(snapshot)
    if owners is None:
        return _result("rejected", "invalid_snapshot_ownership", fingerprint)
    actions = {"self": self_action, "opponent": opponent_action}
    candidates = {"self": self_candidate, "opponent": opponent_candidate}
    for side in ("self", "opponent"):
        reason = _validate_action(actions[side], expected=owners[side])
        if reason is not None:
            return _result("rejected", reason, fingerprint)
        reason = _validate_candidate_binding(candidates[side], actions[side])
        if reason is not None:
            return _result("rejected", reason, fingerprint)
    if _action_category(opponent_action) not in _DIRECT_CATEGORIES:
        return _result("unsupported", "opponent_action_not_direct_damage", fingerprint)
    if action_order.get("status") == "speed_tie":
        return _result("incomplete", "speed_tie", fingerprint)
    if action_order.get("status") != "acts_first":
        if action_order.get("status") == "unsupported_mechanic":
            return _result("unsupported", str(action_order.get("unsupported_reason") or "action_order_unsupported"), fingerprint)
        return _result("incomplete", "self_stage_action_not_first", fingerprint, missing_inputs=action_order.get("missing_inputs"))
    if not _order_matches_actions(action_order, actions):
        return _result("rejected", "action_order_action_mismatch", fingerprint)
    for side in ("self", "opponent"):
        if _trusted_active_hp(snapshot, side) is None:
            return _result("incomplete", f"{side}_exact_hp", fingerprint)

    from llm.advisor_hypothetical_stage_effects import apply_predicted_stage_change, project_self_stage_change
    effect = project_self_stage_change(branch_state=_initial_next_state(snapshot, owners), action=self_action, expected_owner=owners["self"])
    if effect["status"] != "resolved":
        return _result(effect["status"], effect["reason"], fingerprint)
    next_state = _initial_next_state(snapshot, owners)
    apply_predicted_stage_change(next_state, effect)
    from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
    evaluated = evaluate_hypothetical_direct_mechanics(
        branch_state=next_state, source_snapshot_fingerprint=fingerprint,
        action=opponent_action, expected_owner=owners["opponent"], direct_evaluation_input=second_direct_evaluation_input,
    )
    if evaluated.get("status") != "known":
        status = "unsupported" if evaluated.get("status") == "unsupported_mechanic" else "rejected" if evaluated.get("status") == "rejected" else "incomplete"
        return _result(status, str(evaluated.get("reason") or "post_stage_direct_mechanics"), fingerprint, missing_inputs=evaluated.get("missing_inputs"))
    second_candidate = {**deepcopy(dict(opponent_candidate)), "mechanics_result": deepcopy(evaluated["mechanics_result"])}
    direct = _apply_exact_direct_damage(state=next_state, actor_side="opponent", target_side="self", action=opponent_action, candidate=second_candidate)
    if direct["status"] != "resolved":
        return _result(direct["status"], direct["reason"], fingerprint, missing_inputs=direct.get("missing_inputs"))
    trace = [
        {"sequence": 1, "actor_side": "self", "action": _public_action(self_action), "execution_status": "executed", "consequence": "exact_self_stage_change", "stat": effect["stat"], "previous_stage": effect["previous_stage"], "delta": effect["delta"], "projected_stage": effect["projected_stage"]},
        _executed_trace(sequence=2, actor_side="opponent", action=opponent_action, target=owners["self"], outcome=direct),
    ]
    return _resolved(fingerprint, owners, action_order, trace, next_state, "self_stage_then_terminal_direct_ko" if direct["terminal"] else "self_stage_then_exact_direct_damage")


def project_self_poison_then_direct_branch(
    *, turn_snapshot: Any, self_action: Mapping[str, Any], opponent_action: Mapping[str, Any],
    self_candidate: Mapping[str, Any], opponent_candidate: Mapping[str, Any], action_order: Mapping[str, Any],
    second_direct_evaluation_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Project a supported immediate move-poison overlay before one direct action."""
    snapshot = _serialize_snapshot(turn_snapshot)
    if snapshot is None:
        return _result("rejected", "invalid_frozen_snapshot")
    fingerprint = _fingerprint(snapshot)
    owners = _snapshot_owners(snapshot)
    if fingerprint is None or owners is None:
        return _result("rejected", "invalid_snapshot_ownership", fingerprint)
    for action, candidate, owner in ((self_action, self_candidate, owners["self"]), (opponent_action, opponent_candidate, owners["opponent"])):
        reason = _validate_action(action, expected=owner) or _validate_candidate_binding(candidate, action)
        if reason is not None:
            return _result("rejected", reason, fingerprint)
    if _action_category(opponent_action) not in _DIRECT_CATEGORIES:
        return _result("unsupported", "opponent_action_not_direct_damage", fingerprint)
    if action_order.get("status") == "speed_tie":
        return _result("incomplete", "speed_tie", fingerprint)
    if action_order.get("status") != "acts_first":
        return _result("incomplete", "self_poison_action_not_first", fingerprint)
    if not _order_matches_actions(action_order, {"self": self_action, "opponent": opponent_action}):
        return _result("rejected", "action_order_action_mismatch", fingerprint)
    for side in ("self", "opponent"):
        if _trusted_active_hp(snapshot, side) is None:
            return _result("incomplete", f"{side}_exact_hp", fingerprint)
    from llm.advisor_hypothetical_condition_effects import apply_predicted_condition, project_move_poison_condition
    next_state = _initial_next_state(snapshot, owners)
    effect = project_move_poison_condition(branch_state=next_state, action=self_action, expected_owner=owners["self"], target_owner=owners["opponent"])
    if effect.get("status") != "resolved":
        return _result(effect["status"], effect["reason"], fingerprint)
    if effect.get("applicable") is not True:
        return _result("unsupported", effect["reason"], fingerprint)
    apply_predicted_condition(next_state, effect, source_snapshot_fingerprint=fingerprint, branch_state_fingerprint=_fingerprint(next_state))
    from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
    evaluated = evaluate_hypothetical_direct_mechanics(branch_state=next_state, source_snapshot_fingerprint=fingerprint, action=opponent_action, expected_owner=owners["opponent"], direct_evaluation_input=second_direct_evaluation_input)
    if evaluated.get("status") != "known":
        status = "unsupported" if evaluated.get("status") == "unsupported_mechanic" else "rejected" if evaluated.get("status") == "rejected" else "incomplete"
        return _result(status, str(evaluated.get("reason") or "post_poison_direct_mechanics"), fingerprint, missing_inputs=evaluated.get("missing_inputs"))
    direct = _apply_exact_direct_damage(state=next_state, actor_side="opponent", target_side="self", action=opponent_action, candidate={**deepcopy(dict(opponent_candidate)), "mechanics_result": deepcopy(evaluated["mechanics_result"])})
    if direct["status"] != "resolved":
        return _result(direct["status"], direct["reason"], fingerprint, missing_inputs=direct.get("missing_inputs"))
    trace = [
        {"sequence": 1, "actor_side": "self", "action": _public_action(self_action), "execution_status": "executed", "consequence": "predicted_move_poison_condition", "condition": effect["ailment"], "target": deepcopy(dict(owners["opponent"])), "provenance": "turn_engine_predicted_move_poison"},
        _executed_trace(sequence=2, actor_side="opponent", action=opponent_action, target=owners["self"], outcome=direct),
    ]
    return _resolved(fingerprint, owners, action_order, trace, next_state, "self_poison_then_terminal_direct_ko" if direct["terminal"] else "self_poison_then_exact_direct_damage")


def project_self_recovery_direct_branch(
    *,
    turn_snapshot: Any,
    self_action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
    self_candidate: Mapping[str, Any],
    opponent_candidate: Mapping[str, Any],
    action_order: Mapping[str, Any],
    opponent_direct_evaluation_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one exact self recovery and one owned opponent direct action."""
    snapshot = _serialize_snapshot(turn_snapshot)
    if snapshot is None:
        return _result("rejected", "invalid_frozen_snapshot")
    fingerprint = _fingerprint(snapshot)
    if fingerprint is None:
        return _result("rejected", "unserializable_frozen_snapshot")
    owners = _snapshot_owners(snapshot)
    if owners is None:
        return _result("rejected", "invalid_snapshot_ownership", fingerprint)
    actions = {"self": self_action, "opponent": opponent_action}
    candidates = {"self": self_candidate, "opponent": opponent_candidate}
    for side in ("self", "opponent"):
        reason = _validate_action(actions[side], expected=owners[side])
        if reason is not None:
            return _result("rejected", reason, fingerprint)
        reason = _validate_candidate_binding(candidates[side], actions[side])
        if reason is not None:
            return _result("rejected", reason, fingerprint)
    if _action_category(opponent_action) not in _DIRECT_CATEGORIES:
        return _result("unsupported", "opponent_action_not_direct_damage", fingerprint)
    order_status = action_order.get("status") if isinstance(action_order, Mapping) else None
    if order_status == "speed_tie":
        return _result("incomplete", "speed_tie", fingerprint)
    if order_status == "unsupported_mechanic":
        return _result("unsupported", str(action_order.get("unsupported_reason") or "action_order_unsupported"), fingerprint)
    if order_status not in {"acts_first", "acts_second"}:
        return _result("incomplete", "action_order", fingerprint, missing_inputs=action_order.get("missing_inputs") if isinstance(action_order, Mapping) else None)
    if not _order_matches_actions(action_order, actions):
        return _result("rejected", "action_order_action_mismatch", fingerprint)
    for side in ("self", "opponent"):
        if _trusted_active_hp(snapshot, side) is None:
            return _result("incomplete", f"{side}_exact_hp", fingerprint)

    from llm.advisor_hypothetical_recovery_effects import project_self_recovery
    next_state = _initial_next_state(snapshot, owners)
    trace: list[dict[str, Any]] = []
    if order_status == "acts_second":
        first = _apply_exact_direct_damage(state=next_state, actor_side="opponent", target_side="self", action=opponent_action, candidate=opponent_candidate)
        if first["status"] != "resolved":
            return _result(first["status"], first["reason"], fingerprint, missing_inputs=first.get("missing_inputs"))
        trace.append(_executed_trace(sequence=1, actor_side="opponent", action=opponent_action, target=owners["self"], outcome=first))
        if first["terminal"]:
            trace.append({"sequence": 2, "actor_side": "self", "action": _public_action(self_action), "execution_status": "skipped", "reason": "actor_fainted_by_terminal_first_action"})
            return _resolved(fingerprint, owners, action_order, trace, next_state, "guaranteed_terminal_direct_ko")
        recovery = project_self_recovery(branch_state=next_state, action=self_action, expected_owner=owners["self"])
        if recovery["status"] != "resolved":
            return _result(recovery["status"], recovery["reason"], fingerprint)
        _apply_exact_self_recovery(next_state, recovery)
        trace.append(_recovery_trace(sequence=2, action=self_action, recovery=recovery))
        return _resolved(fingerprint, owners, action_order, trace, next_state, "exact_direct_damage_then_self_recovery")

    recovery = project_self_recovery(branch_state=next_state, action=self_action, expected_owner=owners["self"])
    if recovery["status"] != "resolved":
        return _result(recovery["status"], recovery["reason"], fingerprint)
    _apply_exact_self_recovery(next_state, recovery)
    trace.append(_recovery_trace(sequence=1, action=self_action, recovery=recovery))
    if not isinstance(opponent_direct_evaluation_input, Mapping):
        return _result("incomplete", "post_recovery_direct_mechanics_evidence", fingerprint)
    from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
    evaluated = evaluate_hypothetical_direct_mechanics(
        branch_state=next_state, source_snapshot_fingerprint=fingerprint,
        action=opponent_action, expected_owner=owners["opponent"], direct_evaluation_input=opponent_direct_evaluation_input,
    )
    if evaluated.get("status") != "known":
        status = "unsupported" if evaluated.get("status") == "unsupported_mechanic" else "rejected" if evaluated.get("status") == "rejected" else "incomplete"
        return _result(status, str(evaluated.get("reason") or "post_recovery_direct_mechanics"), fingerprint, missing_inputs=evaluated.get("missing_inputs"))
    second = _apply_exact_direct_damage(
        state=next_state, actor_side="opponent", target_side="self", action=opponent_action,
        candidate={**deepcopy(dict(opponent_candidate)), "mechanics_result": deepcopy(evaluated["mechanics_result"])},
    )
    if second["status"] != "resolved":
        return _result(second["status"], second["reason"], fingerprint, missing_inputs=second.get("missing_inputs"))
    trace.append(_executed_trace(sequence=2, actor_side="opponent", action=opponent_action, target=owners["self"], outcome=second))
    return _resolved(fingerprint, owners, action_order, trace, next_state, "self_recovery_then_terminal_direct_ko" if second["terminal"] else "self_recovery_then_exact_direct_damage")


def _serialize_snapshot(value: Any) -> dict[str, Any] | None:
    try:
        raw = value.to_dict() if hasattr(value, "to_dict") else value
        return deepcopy(dict(raw)) if isinstance(raw, Mapping) else None
    except (AttributeError, TypeError, ValueError):
        return None


def _snapshot_owners(snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    state = snapshot.get("battle_state")
    current = snapshot.get("current_state")
    if not isinstance(state, Mapping) or not isinstance(current, Mapping):
        return None
    session_id = current.get("current_state_session_id")
    if not isinstance(session_id, str) or not session_id:
        return None
    slots = {"self": state.get("active_player"), "opponent": state.get("active_opponent")}
    result: dict[str, dict[str, Any]] = {}
    for side, slot in slots.items():
        if not isinstance(slot, Mapping):
            return None
        slot_index, pokemon_id = slot.get("slot_index"), slot.get("species_id")
        if not isinstance(slot_index, int) or isinstance(slot_index, bool) or slot_index < 0 or not isinstance(pokemon_id, str) or not pokemon_id:
            return None
        result[side] = {"session_id": session_id, "side": side, "slot_index": slot_index, "pokemon_id": pokemon_id}
    return result


def _validate_action(action: Any, *, expected: Mapping[str, Any]) -> str | None:
    if not isinstance(action, Mapping):
        return "invalid_action"
    owner = action.get("owner")
    move = action.get("move")
    if not isinstance(owner, Mapping) or not isinstance(move, Mapping):
        return "invalid_action_shape"
    if dict(owner) != dict(expected):
        return "stale_or_mismatched_action_owner"
    move_id, slot_index = move.get("move_id"), move.get("slot_index")
    if not isinstance(move_id, str) or not move_id or not isinstance(slot_index, int) or isinstance(slot_index, bool) or not 0 <= slot_index < 4:
        return "invalid_action_move_ownership"
    return None


def _validate_candidate_binding(candidate: Any, action: Mapping[str, Any]) -> str | None:
    if not isinstance(candidate, Mapping):
        return "invalid_candidate_evidence"
    move = action["move"]
    if candidate.get("move") != move["move_id"] or candidate.get("slot_index") != move["slot_index"]:
        return "candidate_action_mismatch"
    return None


def _action_category(action: Mapping[str, Any]) -> Any:
    move = action.get("move")
    return move.get("category") if isinstance(move, Mapping) else None


def _order_matches_actions(order: Mapping[str, Any], actions: Mapping[str, Mapping[str, Any]]) -> bool:
    for side in ("self", "opponent"):
        reference = order.get(f"{side}_action")
        move = actions[side].get("move")
        if not isinstance(reference, Mapping) or not isinstance(move, Mapping):
            return False
        if reference.get("move_id") != move.get("move_id") or reference.get("priority") != move.get("priority"):
            return False
    return True


def _certain_move_success(candidate: Mapping[str, Any]) -> bool:
    accuracy = candidate.get("accuracy_evidence")
    if not isinstance(accuracy, Mapping):
        return False
    if accuracy.get("status") == "always_hits":
        return True
    return accuracy.get("status") == "known_accuracy" and accuracy.get("adjusted_accuracy", accuracy.get("canonical_accuracy")) == 100


def _trusted_active_hp(snapshot: Mapping[str, Any], side: str) -> dict[str, int] | None:
    current = snapshot.get("current_state")
    hp_context = current.get("current_hp_context") if isinstance(current, Mapping) else None
    entries = hp_context.get("current_hp") if isinstance(hp_context, Mapping) else None
    if not isinstance(entries, list):
        return None
    entry = next((item for item in entries if isinstance(item, Mapping) and item.get("side") == side), None)
    if not isinstance(entry, Mapping) or entry.get("status") != "user_confirmed" or entry.get("source") != "user_confirmed_current_hp" or entry.get("confidence") != "known":
        return None
    hp, maximum = entry.get("current_hp"), entry.get("maximum_hp")
    if isinstance(hp, bool) or isinstance(maximum, bool) or not isinstance(hp, int) or not isinstance(maximum, int) or not 1 <= hp <= maximum:
        return None
    return {"current_hp": hp, "max_hp": maximum}


def _damage_bounds(mechanics: Mapping[str, Any]) -> tuple[int, int] | None:
    damage = mechanics.get("damage_range")
    if not isinstance(damage, Mapping):
        return None
    minimum, maximum = damage.get("minimum"), damage.get("maximum")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (minimum, maximum)) or minimum > maximum:
        return None
    return minimum, maximum


def _initial_next_state(snapshot: Mapping[str, Any], owners: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    active: dict[str, dict[str, Any]] = {}
    for side in ("self", "opponent"):
        hp = _trusted_active_hp(snapshot, side)
        if hp is None:
            raise ValueError("exact_hp_required_before_projection")
        active[side] = {**deepcopy(dict(owners[side])), "current_hp": hp["current_hp"], "max_hp": hp["max_hp"], "fainted": False}
    state = {
        "schema_version": "deterministic-transition-preview-v1",
        "active": active,
        "current_state": deepcopy(dict(snapshot.get("current_state", {}))),
    }
    # A next-turn snapshot may carry branch-only predictive overlays through
    # the explicit lifecycle handoff.  They remain overlays, never observed
    # current-state facts, and are validated by their existing consumers.
    overlays = snapshot.get("turn_engine_branch_overlays")
    if isinstance(overlays, Mapping):
        for key in ("predicted_stage_context", "predicted_condition_context", "predicted_toxic_lifecycle"):
            if key in overlays:
                state[key] = deepcopy(overlays[key])
        # Handoff preserves predictive origin separately from the binding for
        # this newly frozen turn.  Rebind only the detached overlay, never the
        # reducer-observed condition record.
        condition = state.get("predicted_condition_context")
        if isinstance(condition, dict):
            source = _fingerprint(snapshot)
            if isinstance(source, str):
                condition.setdefault("predictive_origin_source_snapshot_fingerprint", condition.get("source_snapshot_fingerprint"))
                condition["source_snapshot_fingerprint"] = source
                lifecycle = state.get("predicted_toxic_lifecycle")
                if isinstance(lifecycle, dict):
                    lifecycle.setdefault("predictive_origin_source_snapshot_fingerprint", lifecycle.get("source_snapshot_fingerprint"))
                    lifecycle["source_snapshot_fingerprint"] = source
                base = deepcopy(state)
                base.pop("predicted_condition_context", None)
                binding = _fingerprint(base)
                condition["branch_state_fingerprint"] = binding
                if isinstance(lifecycle, dict):
                    lifecycle["branch_state_fingerprint"] = binding
    return state


def _apply_exact_direct_damage(*, state: Mapping[str, Any], actor_side: str, target_side: str, action: Mapping[str, Any], candidate: Any) -> dict[str, Any]:
    active = state.get("active") if isinstance(state, Mapping) else None
    actor = active.get(actor_side) if isinstance(active, Mapping) else None
    target = active.get(target_side) if isinstance(active, Mapping) else None
    if not isinstance(actor, Mapping) or not isinstance(target, dict) or actor.get("fainted") is not False or target.get("fainted") is not False:
        return {"status": "incomplete", "reason": "active_execution_state"}
    if _action_category(action) not in _DIRECT_CATEGORIES:
        return {"status": "unsupported", "reason": "action_not_direct_damage"}
    if not isinstance(candidate, Mapping):
        return {"status": "rejected", "reason": "invalid_candidate_evidence"}
    mechanics = candidate.get("mechanics_result")
    mechanics_status = mechanics.get("status") if isinstance(mechanics, Mapping) else None
    if mechanics_status == "unsupported_mechanic":
        return {"status": "unsupported", "reason": str(mechanics.get("unsupported_reason") or "direct_mechanics_unsupported")}
    if mechanics_status != "known":
        return {"status": "incomplete", "reason": "direct_mechanics", "missing_inputs": mechanics.get("missing_inputs") if isinstance(mechanics, Mapping) else None}
    if mechanics.get("mechanics_source") not in _NATIVE_SOURCES:
        return {"status": "unsupported", "reason": "non_native_direct_mechanics"}
    if mechanics.get("hit_count") != 1:
        return {"status": "unsupported", "reason": "multi_hit_uncertainty"}
    if not _certain_move_success(candidate):
        return {"status": "incomplete", "reason": "move_success_uncertain"}
    bounds = _damage_bounds(mechanics)
    ko = mechanics.get("ko_result")
    current_hp = target.get("current_hp")
    if bounds is None or not isinstance(current_hp, int) or isinstance(current_hp, bool) or current_hp < 1 or not isinstance(ko, Mapping) or ko.get("status") != "resolved":
        return {"status": "incomplete", "reason": "exact_damage_outcome"}
    minimum, maximum = bounds
    guaranteed_terminal = minimum >= current_hp and ko.get("single_hit_probability") == 1.0
    if minimum != maximum and not guaranteed_terminal:
        return {"status": "incomplete", "reason": "non_unique_damage_outcome"}
    exact_damage = minimum if minimum == maximum else current_hp
    post_hp = max(0, current_hp - exact_damage)
    terminal = post_hp == 0
    if terminal and not guaranteed_terminal and ko.get("single_hit_probability") != 1.0:
        return {"status": "incomplete", "reason": "exact_terminal_ko_evidence"}
    target["current_hp"] = post_hp
    target["fainted"] = terminal
    _sync_branch_hp(state, target_side=target_side, current_hp=post_hp, maximum_hp=target.get("max_hp"))
    return {"status": "resolved", "terminal": terminal, "damage": exact_damage, "damage_range": deepcopy(dict(mechanics["damage_range"])), "post_hp": post_hp}


def _sync_branch_hp(state: Mapping[str, Any], *, target_side: str, current_hp: int, maximum_hp: Any) -> None:
    current = state.get("current_state") if isinstance(state, Mapping) else None
    if not isinstance(current, dict) or not isinstance(maximum_hp, int) or isinstance(maximum_hp, bool):
        return
    hp_context = current.get("current_hp_context")
    entries = hp_context.get("current_hp") if isinstance(hp_context, Mapping) else None
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("side") == target_side:
                entry["current_hp"] = current_hp
                entry["maximum_hp"] = maximum_hp
    direct = current.get("direct_mechanics_context")
    if isinstance(direct, Mapping):
        side = direct.get("attacker" if target_side == "self" else "defender")
        if isinstance(side, dict):
            side["current_hp"] = current_hp
            side["max_hp"] = maximum_hp


def _apply_exact_self_recovery(state: Mapping[str, Any], recovery: Mapping[str, Any]) -> None:
    active = state.get("active") if isinstance(state, Mapping) else None
    actor = active.get("self") if isinstance(active, Mapping) else None
    if not isinstance(actor, dict) or actor.get("fainted") is not False:
        raise ValueError("invalid_recovery_execution_state")
    if actor.get("current_hp") != recovery.get("hp_before") or actor.get("max_hp") != recovery.get("max_hp"):
        raise ValueError("recovery_hp_branch_mismatch")
    actor["current_hp"] = recovery["hp_after"]
    _sync_branch_hp(state, target_side="self", current_hp=recovery["hp_after"], maximum_hp=recovery["max_hp"])


def _recovery_trace(*, sequence: int, action: Mapping[str, Any], recovery: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "actor_side": "self",
        "action": _public_action(action),
        "execution_status": "executed",
        "consequence": "exact_self_recovery",
        "recovery": recovery["recovery"],
        "hp_before": recovery["hp_before"],
        "post_hp": recovery["hp_after"],
    }


def _executed_trace(*, sequence: int, actor_side: str, action: Mapping[str, Any], target: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "actor_side": actor_side,
        "action": _public_action(action),
        "execution_status": "executed",
        "consequence": "guaranteed_terminal_ko" if outcome["terminal"] else "exact_nonterminal_direct_damage",
        "target": deepcopy(dict(target)),
        "damage": outcome["damage"],
        "damage_range": deepcopy(outcome["damage_range"]),
        "post_hp": outcome["post_hp"],
    }


def _resolved(fingerprint: str, owners: Mapping[str, Mapping[str, Any]], action_order: Mapping[str, Any], trace: list[dict[str, Any]], next_state: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "status": "resolved",
        "reason": reason,
        "source_snapshot_fingerprint": fingerprint,
        "source_ownership": deepcopy(dict(owners)),
        "action_order": deepcopy(dict(action_order)),
        "consequence_trace": deepcopy(trace),
        "next_state": deepcopy(dict(next_state)),
        "boundary": {"phase": "pre_end_of_turn", "end_of_turn": "not_entered"},
        "limitations": [
            "exact_direct_damage_only",
            "post_first_evidence_must_be_branch_bound",
            "no_reducer_or_runtime_writeback",
            "no_item_consumption_or_end_of_turn_projection",
        ],
    }


def _public_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {"owner": deepcopy(dict(action["owner"])), "move": deepcopy(dict(action["move"]))}


def _fingerprint(snapshot: Mapping[str, Any]) -> str | None:
    try:
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return sha256(encoded).hexdigest()


def fingerprint_transition_preview_state(state: Mapping[str, Any]) -> str | None:
    """Return the canonical detached-state binding used for continuation evidence."""
    return _fingerprint(state)


def _result(status: str, reason: str, fingerprint: str | None = None, *, missing_inputs: Any = None) -> dict[str, Any]:
    result = {"status": status, "reason": reason, "source_snapshot_fingerprint": fingerprint, "consequence_trace": [], "next_state": None, "boundary": {"phase": "pre_end_of_turn", "end_of_turn": "not_entered"}}
    if isinstance(missing_inputs, list):
        result["missing_inputs"] = deepcopy(missing_inputs)
    return result
