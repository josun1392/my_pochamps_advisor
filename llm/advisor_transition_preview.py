"""Pure, fail-closed deterministic transition previews.

This Practical 2.0 slice supports only exact direct-damage transitions.  It is
not a reducer, a damage calculator, or a turn simulator.
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
    return {
        "schema_version": "deterministic-transition-preview-v1",
        "active": active,
        "current_state": deepcopy(dict(snapshot.get("current_state", {}))),
    }


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
