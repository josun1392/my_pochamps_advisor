"""Atomic canonical writeback for exact Champions paralysis applications."""
from copy import deepcopy

from llm.advisor_champions_paralysis_application import (
    freeze_champions_paralysis_application,
    materialize_champions_paralysis_application,
)
from llm.advisor_lifecycle_confirmation import (
    HP_TRANSITION_SOURCE, PARALYSIS_APPLICATION_SOURCE, USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def admit_champions_paralysis_application(*, runtime_session_manager, captured_session_id, target_side, move_id, action_id, move_success_authority, turn_number, hp_after=None, reflection_authority=None):
    """Validate exact move evidence, then write only canonical condition facts."""
    if target_side not in {"self", "opponent"} or move_id not in {"thunder-wave", "nuzzle"} or not isinstance(action_id, str) or not action_id:
        return _result("rejected", "invalid_paralysis_application_input")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected", "runtime_snapshot_unavailable")
    target = _active_owner(snapshot["state"], target_side)
    actor = _active_owner(snapshot["state"], _opposite(target_side))
    if target is None or actor is None or target.get("fainted") is True:
        return _result("rejected", "invalid_paralysis_application_owner")
    target_owner, actor_owner = _owner(captured_session_id, target_side, target), _owner(captured_session_id, _opposite(target_side), actor)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor_owner)
    action = {"action_id": action_id, "action_type": "attack", "identity": move_id}
    authority = freeze_champions_paralysis_application(
        strategy_d0=d0, runtime_snapshot=snapshot, actor=actor_owner, target=target_owner,
        action=action, move_success_authority=move_success_authority,
        reflection_authority=reflection_authority,
    )
    if authority.get("status") != "resolved":
        return _result(authority.get("status", "rejected"), authority.get("reason", "paralysis_authority_unavailable"))
    materialized = materialize_champions_paralysis_application(authority=authority, runtime_snapshot=snapshot)
    if materialized.get("status") != "resolved":
        return _result("rejected", materialized.get("reason", "paralysis_materialization_rejected"))
    hp_transition = _nuzzle_transition(move_id, target, hp_after)
    if isinstance(hp_transition, str):
        return _result("rejected", hp_transition)
    # A fainted post-hit target never receives a usable major condition.
    applies = materialized.get("paralysis_applied") is True and not (hp_transition and hp_transition[1] == 0)
    if not applies and hp_transition is None:
        return {"status": "resolved", "outcome": materialized.get("outcome"), "observation_transaction": []}
    return _commit(runtime_session_manager, captured_session_id, snapshot, target_owner, hp_transition, applies, turn_number, materialized.get("outcome"))


def _commit(manager, session, snapshot, target, hp_transition, applies, turn_number, outcome):
    owners = {side: _owner(session, side, _active_owner(snapshot["state"], side)) for side in ("self", "opponent")}
    boundary = LifecycleConfirmationBoundary(session, owners)
    confirmations = []
    if hp_transition is not None:
        sequence = manager.allocate_observation_sequence()["observation_sequence"]
        result = boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before": hp_transition[0], "hp_after": hp_transition[1]}, session_id=session, source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side=target["side"], slot_index=target["slot_index"], pokemon_id=target["pokemon_id"], observation_id=f"{session}:nuzzle-hp:{sequence}", turn_number=turn_number)
        if result.get("status") != "confirmed": return _result("rejected", "hp_confirmation_rejected")
        result["observation"]["observation_sequence"] = sequence; confirmations.append(result)
    if applies:
        sequence = manager.allocate_observation_sequence()["observation_sequence"]
        result = boundary.confirm(event_kind="current_condition_observed", payload={"condition": "paralysis"}, session_id=session, source=PARALYSIS_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side=target["side"], slot_index=target["slot_index"], pokemon_id=target["pokemon_id"], observation_id=f"{session}:paralysis:{sequence}", turn_number=turn_number)
        if result.get("status") != "confirmed": return _result("rejected", "paralysis_condition_confirmation_rejected")
        result["observation"]["observation_sequence"] = sequence; confirmations.append(result)
    collection = manager.read_collection_snapshot()
    rows = [*collection.get("ordered_observations", []), *(item["observation"] for item in confirmations)]
    rows.sort(key=lambda item: (item["observation_sequence"], item["observation_id"]))
    if manager.preview(session, {**collection, "ordered_observations": rows}).get("status") != "preview_ready": return _result("rejected", "atomic_paralysis_preview_rejected")
    admitted = manager.admit_confirmations_atomically(session, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}: return _result("rejected", "atomic_paralysis_admission_rejected")
    applied = manager.apply(session, manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}: return _result("rejected", "atomic_paralysis_application_rejected")
    return {"status": "resolved", "outcome": outcome, "observation_transaction": [deepcopy(item["observation"]) for item in confirmations]}


def _nuzzle_transition(move_id, target, hp_after):
    if move_id != "nuzzle": return None
    before = target.get("current_hp")
    if not isinstance(before, int) or isinstance(before, bool) or not isinstance(hp_after, int) or isinstance(hp_after, bool) or hp_after < 0 or hp_after >= before:
        return "nuzzle_exact_post_hit_hp_required"
    return before, hp_after


def _active_owner(state, side):
    current = state.get(f"{side}_side", {}) if isinstance(state, dict) else {}
    slot = current.get("active_slot_index"); pokemon = current.get("pokemon", {}).get(slot)
    return {**pokemon, "_active_slot_index": slot} if isinstance(slot, int) and isinstance(pokemon, dict) else None


def _owner(session, side, pokemon):
    current = pokemon if isinstance(pokemon, dict) else {}
    return {"session_id": session, "side": side, "slot_index": current.get("_active_slot_index", 0), "pokemon_id": current.get("pokemon_id")}


def _opposite(side): return "opponent" if side == "self" else "self"
def _result(status, reason): return {"status": status, "reason": reason, "observation_transaction": []}
