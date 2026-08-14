"""Pure, fail-closed deterministic transition previews.

This Practical 2.0 slice intentionally supports only a first-actor direct move
whose existing native mechanics evidence proves a one-hit terminal KO.  It is
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
    """Project one exact terminal-KO branch from frozen, existing evidence.

    ``self_candidate`` and ``opponent_candidate`` are already-produced
    candidate/direct-mechanics evidence.  This adapter deliberately does not
    recalculate mechanics or promote a damage range into an exact HP value.
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

    first_side = "self" if order_status == "acts_first" else "opponent"
    target_side = "opponent" if first_side == "self" else "self"
    mechanics = candidates[first_side].get("mechanics_result")
    mechanics_status = mechanics.get("status") if isinstance(mechanics, Mapping) else None
    if mechanics_status == "unsupported_mechanic":
        return _result("unsupported", str(mechanics.get("unsupported_reason") or "direct_mechanics_unsupported"), fingerprint)
    if mechanics_status != "known":
        missing = mechanics.get("missing_inputs") if isinstance(mechanics, Mapping) else None
        return _result("incomplete", "direct_mechanics", fingerprint, missing_inputs=missing)
    if mechanics.get("mechanics_source") not in _NATIVE_SOURCES:
        return _result("unsupported", "non_native_direct_mechanics", fingerprint)
    if mechanics.get("hit_count") != 1:
        return _result("unsupported", "multi_hit_uncertainty", fingerprint)
    if not _certain_move_success(candidates[first_side]):
        return _result("incomplete", "move_success_uncertain", fingerprint)

    actor_hp = _trusted_active_hp(snapshot, first_side)
    if actor_hp is None:
        return _result("incomplete", f"{first_side}_exact_hp", fingerprint)
    target_hp = _trusted_active_hp(snapshot, target_side)
    if target_hp is None:
        return _result("incomplete", f"{target_side}_exact_hp", fingerprint)
    minimum_damage = _minimum_damage(mechanics)
    ko = mechanics.get("ko_result")
    if minimum_damage is None or not isinstance(ko, Mapping) or ko.get("status") != "resolved" or ko.get("single_hit_probability") != 1.0:
        return _result("incomplete", "non_terminal_damage_range", fingerprint)
    if minimum_damage < target_hp["current_hp"]:
        return _result("incomplete", "non_terminal_damage_range", fingerprint)

    next_state = _detached_next_state(snapshot, owners, target_side, target_hp)
    trace = [
        {
            "sequence": 1,
            "actor_side": first_side,
            "action": _public_action(actions[first_side]),
            "execution_status": "executed",
            "consequence": "guaranteed_terminal_ko",
            "target": deepcopy(owners[target_side]),
            "damage_range": deepcopy(mechanics.get("damage_range")),
        },
        {
            "sequence": 2,
            "actor_side": target_side,
            "action": _public_action(actions[target_side]),
            "execution_status": "skipped",
            "reason": "actor_fainted_by_terminal_first_action",
        },
    ]
    return {
        "status": "resolved",
        "reason": "guaranteed_terminal_direct_ko",
        "source_snapshot_fingerprint": fingerprint,
        "source_ownership": deepcopy(owners),
        "action_order": deepcopy(dict(action_order)),
        "consequence_trace": trace,
        "next_state": next_state,
        "boundary": {"phase": "pre_end_of_turn", "end_of_turn": "not_entered"},
        "limitations": [
            "terminal_guaranteed_ko_only",
            "no_reducer_or_runtime_writeback",
            "no_item_consumption_or_end_of_turn_projection",
        ],
    }


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


def _minimum_damage(mechanics: Mapping[str, Any]) -> int | None:
    damage = mechanics.get("damage_range")
    value = damage.get("minimum") if isinstance(damage, Mapping) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _detached_next_state(snapshot: Mapping[str, Any], owners: Mapping[str, Mapping[str, Any]], target_side: str, target_hp: Mapping[str, int]) -> dict[str, Any]:
    active: dict[str, dict[str, Any]] = {}
    for side in ("self", "opponent"):
        hp = _trusted_active_hp(snapshot, side)
        assert hp is not None
        active[side] = {**deepcopy(dict(owners[side])), "current_hp": hp["current_hp"], "max_hp": hp["max_hp"], "fainted": False}
    active[target_side]["current_hp"] = 0
    active[target_side]["max_hp"] = target_hp["max_hp"]
    active[target_side]["fainted"] = True
    return {"schema_version": "deterministic-transition-preview-v1", "active": active}


def _public_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {"owner": deepcopy(dict(action["owner"])), "move": deepcopy(dict(action["move"]))}


def _fingerprint(snapshot: Mapping[str, Any]) -> str | None:
    try:
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return sha256(encoded).hexdigest()


def _result(status: str, reason: str, fingerprint: str | None = None, *, missing_inputs: Any = None) -> dict[str, Any]:
    result = {"status": status, "reason": reason, "source_snapshot_fingerprint": fingerprint, "consequence_trace": [], "next_state": None, "boundary": {"phase": "pre_end_of_turn", "end_of_turn": "not_entered"}}
    if isinstance(missing_inputs, list):
        result["missing_inputs"] = deepcopy(missing_inputs)
    return result
