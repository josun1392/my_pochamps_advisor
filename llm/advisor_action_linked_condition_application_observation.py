"""Production admission for an exact C5 action-linked target-condition application."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_detached_observed_rng_reconciliation import (
    link_condition_application_observation_to_predictive_action,
)
from llm.advisor_lifecycle_confirmation import (
    CONDITION_APPLICATION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


_CONDITIONS = {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}


def admit_action_linked_condition_application_observation(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
    executed_move_observation: Mapping[str, Any],
    condition: str,
) -> dict[str, Any]:
    """Commit one newly-applied condition while retaining exact C5 action linkage."""
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id or condition not in _CONDITIONS:
        return _result("rejected", "invalid_condition_application_input")
    if not isinstance(predictive_binding, Mapping) or predictive_binding.get("session_id") != captured_session_id:
        return _result("rejected", "predictive_binding_session_mismatch")

    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected", "runtime_snapshot_unavailable")
    state = snapshot.get("state")
    target = predictive_binding.get("target")
    actor = predictive_binding.get("actor")
    if not _owner_exists(state, target) or not _owner_exists(state, actor):
        return _result("rejected", "predictive_action_owner_not_current")
    target_state = _active_pokemon(state, target.get("side"))
    if not isinstance(target_state, Mapping) or target_state.get("fainted") is True:
        return _result("rejected", "condition_application_target_unavailable")
    # Newly-applied evidence is only exact when the pre-application runtime is
    # explicitly condition-free. Unknown or already-statused targets cannot be
    # upgraded into a secondary-activation fact.
    if target_state.get("condition") is not None:
        return _result("rejected", "target_condition_not_known_none_before_application")

    owners = {
        side: _active_owner(state, captured_session_id, side)
        for side in ("self", "opponent")
    }
    if not all(isinstance(value, dict) for value in owners.values()):
        return _result("rejected", "active_owner_snapshot_incomplete")

    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    boundary = LifecycleConfirmationBoundary(captured_session_id, owners)
    confirmation = boundary.confirm(
        event_kind="condition_applied_observed",
        payload={"condition": condition},
        session_id=captured_session_id,
        source=CONDITION_APPLICATION_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=target["side"],
        slot_index=target["slot_index"],
        pokemon_id=target["pokemon_id"],
        observation_id=f"{captured_session_id}:condition-applied:{sequence}",
        turn_number=predictive_binding.get("turn_number"),
        related_observation_id=executed_move_observation.get("observation_id"),
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "condition_application_confirmation_rejected"))
    observation = deepcopy(confirmation["observation"])
    observation["observation_sequence"] = sequence
    linked = link_condition_application_observation_to_predictive_action(
        observation=observation,
        predictive_binding=predictive_binding,
        predictive_ledger=predictive_ledger,
        executed_move_observation=executed_move_observation,
    )
    if linked.get("event_kind") != "condition_applied_observed" or linked.get("reconciliation_eligible") is not True:
        return _result("rejected", linked.get("reason", "condition_application_action_link_rejected"))
    confirmation = {**deepcopy(confirmation), "observation": linked}

    collection = runtime_session_manager.read_collection_snapshot()
    rows = [*collection.get("ordered_observations", []), deepcopy(linked)]
    rows.sort(key=lambda row: (row.get("observation_sequence"), row.get("observation_id")))
    preview = runtime_session_manager.preview(
        captured_session_id, {**collection, "ordered_observations": rows},
    )
    if preview.get("status") != "preview_ready":
        return _result("rejected", "condition_application_reducer_preview_rejected")
    admitted = runtime_session_manager.admit_confirmation(captured_session_id, confirmation)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "condition_application_observation_admission_rejected")
    applied = runtime_session_manager.apply(
        captured_session_id, runtime_session_manager.read_collection_snapshot(),
    )
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "condition_application_reducer_apply_rejected")
    return {
        "status": "resolved",
        "observation": deepcopy(linked),
        "runtime_committed": True,
        "provenance": "authenticated_c5_action_linked_condition_application_v1",
    }


def _active_pokemon(state: Any, side: Any) -> Mapping[str, Any] | None:
    if not isinstance(state, Mapping) or side not in {"self", "opponent"}:
        return None
    side_state = state.get(f"{side}_side")
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    if not isinstance(roster, Mapping) or not isinstance(slot, int) or isinstance(slot, bool):
        return None
    row = roster.get(slot, roster.get(str(slot)))
    return row if isinstance(row, Mapping) else None


def _active_owner(state: Any, session_id: str, side: str) -> dict[str, Any] | None:
    pokemon = _active_pokemon(state, side)
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(pokemon_id, str) or not pokemon_id:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}


def _owner_exists(state: Any, owner: Any) -> bool:
    if not isinstance(owner, Mapping):
        return False
    current = _active_owner(state, owner.get("session_id"), owner.get("side"))
    return current == {
        "session_id": owner.get("session_id"),
        "side": owner.get("side"),
        "slot_index": owner.get("slot_index"),
        "pokemon_id": owner.get("pokemon_id"),
    }


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason, "observation": None, "runtime_committed": False}
