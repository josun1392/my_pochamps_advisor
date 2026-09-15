"""Production admission for explicit, reducer-owned action-history observations."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_lifecycle_confirmation import EXECUTED_MOVE_SOURCE, PREVIOUS_ACTION_RESULT_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager

_RESULTS = {"accuracy_miss", "type_or_ability_immunity", "move_specific_failure", "full_paralysis", "flinch", "sleep", "freeze", "success", "protection_block", "recharge", "sky_drop"}


def admit_previous_action_history_observation(*, runtime_session_manager: BattleObservationRuntimeSessionManager, captured_session_id: str, side: str, execution_move_id: str, selected_move_id: str, source_action_id: str, result_class: str | None, turn_number: int) -> dict:
    """Atomically preview, admit, and apply one explicit real action observation.

    A None result intentionally records execution only.  The active runtime
    snapshot, rather than UI selection, supplies the exact owner identity.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager): return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id or side not in {"self", "opponent"}: return _result("rejected", "invalid_session_or_side")
    if not _move(execution_move_id) or not _move(selected_move_id) or not _action(source_action_id) or (result_class is not None and result_class not in _RESULTS): return _result("rejected", "invalid_action_history_payload")
    if not isinstance(turn_number, int) or isinstance(turn_number, bool) or turn_number < 1: return _result("rejected", "invalid_turn_number")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready": return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    owner = _active_owner(snapshot.get("state"), side)
    if owner is None: return _result("incomplete", "active_owner_unavailable")
    execution_sequence = runtime_session_manager.allocate_observation_sequence()
    if execution_sequence.get("status") != "allocated" or execution_sequence.get("session_id") != captured_session_id: return _result("rejected", "execution_sequence_unavailable")
    execution_number = execution_sequence["observation_sequence"]
    result_number = None
    if result_class is not None:
        allocated = runtime_session_manager.allocate_observation_sequence()
        if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id: return _result("rejected", "result_sequence_unavailable")
        result_number = allocated["observation_sequence"]
    boundary = LifecycleConfirmationBoundary(captured_session_id, {side: owner})
    execution = boundary.confirm(event_kind="executed_move_observed", payload={"move_id": execution_move_id, "source_action_id": source_action_id}, session_id=captured_session_id, source=EXECUTED_MOVE_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], observation_id=f"{captured_session_id}:executed-move-{execution_number}", turn_number=turn_number)
    if execution.get("status") != "confirmed": return _result("rejected", "execution_confirmation_rejected")
    execution["observation"]["observation_sequence"] = execution_number
    confirmations = [execution]
    if result_class is not None:
        result = boundary.confirm(event_kind="previous_action_result_observed", payload={"previous_action_id": source_action_id, "selected_move_id": selected_move_id, "execution_move_id": execution_move_id, "result_class": result_class}, session_id=captured_session_id, source=PREVIOUS_ACTION_RESULT_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"], observation_id=f"{captured_session_id}:previous-action-result-{result_number}", turn_number=turn_number, related_observation_id=execution["observation"]["observation_id"])
        if result.get("status") != "confirmed": return _result("rejected", "result_confirmation_rejected")
        result["observation"]["observation_sequence"] = result_number
        confirmations.append(result)
    preview_snapshot = _preview(runtime_session_manager.read_collection_snapshot(), confirmations)
    if preview_snapshot is None: return _result("rejected", "invalid_collection_snapshot")
    preview = runtime_session_manager.preview(captured_session_id, preview_snapshot)
    if preview.get("status") != "preview_ready": return _result("rejected", "reducer_preview_rejected")
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}: return _result("rejected", "observation_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}: return _result("rejected", "reducer_application_rejected")
    return {"status": "resolved", "reason": None, "owner": deepcopy(owner), "observations": [deepcopy(row["observation"]) for row in confirmations], "preview": {"status": preview.get("status")}}


def _active_owner(state: object, side: str) -> dict | None:
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None; roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None; slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) and not isinstance(slot, bool) else None
    session_id = state.get("session_id") if isinstance(state, Mapping) else None; pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id} if isinstance(session_id, str) and session_id and isinstance(pokemon_id, str) and pokemon_id and isinstance(slot, int) and not isinstance(slot, bool) and pokemon.get("fainted") is not True else None


def _move(value): return isinstance(value, str) and bool(value) and value == value.lower() and " " not in value and "_" not in value
def _action(value): return _move(value)
def _preview(snapshot, confirmations):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready" or not isinstance(snapshot.get("ordered_observations"), list): return None
    rows = deepcopy(snapshot["ordered_observations"]) + [deepcopy(row["observation"]) for row in confirmations]
    return {**deepcopy(dict(snapshot)), "ordered_observations": sorted(rows, key=lambda row: (row.get("observation_sequence"), row.get("observation_id")))}
def _result(status, reason): return {"status": status, "reason": reason, "owner": None, "observations": [], "preview": None}
