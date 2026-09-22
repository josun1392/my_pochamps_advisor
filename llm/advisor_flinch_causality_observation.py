"""Strict production admission for cross-action C5 flinch causality evidence."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_detached_observed_rng_reconciliation import (
    validate_historical_predictive_action_binding,
)
from llm.advisor_lifecycle_confirmation import (
    FLINCH_CAUSALITY_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager


PROVENANCE = "authenticated_c5_cross_action_flinch_causality_v1"


def admit_flinch_causality_observation(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
    producer_execution_observation: Mapping[str, Any],
    cancelled_execution_observation: Mapping[str, Any],
    cancelled_result_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Admit evidence that producer action A caused flinch cancelling action B."""
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return _result("rejected", checked.get("reason", "predictive_binding_invalid"))
    if checked.get("session_id") != captured_session_id:
        return _result("rejected", "predictive_binding_session_mismatch")
    if checked.get("move_id") != "iron-head":
        return _result("rejected", "unsupported_flinch_producer_for_v1")

    producer_error = _validate_producer_execution(producer_execution_observation, checked)
    if producer_error:
        return _result("rejected", producer_error)

    affected = checked["target"]
    cancelled_error = _validate_cancelled_history(
        cancelled_execution_observation, cancelled_result_observation,
        affected=affected, session_id=checked["session_id"], turn_number=checked["turn_number"],
    )
    if cancelled_error:
        return _result("rejected", cancelled_error)

    producer_action_id = checked["source_action_id"]
    cancelled_payload = _payload(cancelled_execution_observation)
    cancelled_action_id = cancelled_payload.get("source_action_id")
    if producer_action_id == cancelled_action_id:
        return _result("rejected", "producer_and_cancelled_action_must_differ")

    collection = runtime_session_manager.read_collection_snapshot()
    rows = collection.get("ordered_observations") if isinstance(collection, Mapping) else None
    if not isinstance(rows, list):
        return _result("rejected", "observation_collection_unavailable")
    for source in (producer_execution_observation, cancelled_execution_observation, cancelled_result_observation):
        matches = [row for row in rows if row.get("observation_id") == source.get("observation_id")]
        if len(matches) != 1 or matches[0] != source:
            return _result("rejected", "referenced_observation_not_exactly_admitted")

    if len(_execution_matches(rows, checked["actor"], producer_action_id, checked["move_id"], checked["turn_number"])) != 1:
        return _result("rejected", "ambiguous_producer_execution_evidence")
    producer_results = [
        row for row in rows
        if row.get("event_kind") == "previous_action_result_observed"
        and row.get("session_id") == checked["session_id"]
        and row.get("turn_number") == checked["turn_number"]
        and _owner_from_observation(row) == checked["actor"]
        and _payload(row).get("previous_action_id") == producer_action_id
    ]
    if len(producer_results) > 1:
        return _result("rejected", "ambiguous_producer_result_evidence")
    if producer_results and _payload(producer_results[0]).get("result_class") != "success":
        return _result("rejected", "producer_result_incompatible_with_flinch_causality")
    cancelled_move_id = cancelled_payload.get("move_id")
    if len(_execution_matches(rows, affected, cancelled_action_id, cancelled_move_id, checked["turn_number"])) != 1:
        return _result("rejected", "ambiguous_cancelled_execution_evidence")
    result_matches = [
        row for row in rows
        if row.get("event_kind") == "previous_action_result_observed"
        and row.get("session_id") == checked["session_id"]
        and row.get("turn_number") == checked["turn_number"]
        and _owner_from_observation(row) == affected
        and _payload(row).get("previous_action_id") == cancelled_action_id
    ]
    if len(result_matches) != 1 or result_matches[0] != cancelled_result_observation:
        return _result("rejected", "ambiguous_cancelled_result_evidence")

    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_allocation_failed")
    sequence = allocated["observation_sequence"]
    source_sequences = tuple(_sequence(row) for row in (
        producer_execution_observation, cancelled_execution_observation, cancelled_result_observation,
    ))
    if any(value <= 0 for value in source_sequences) or sequence <= max(source_sequences):
        return _result("rejected", "flinch_causality_sequence_not_after_sources")

    state = runtime_session_manager.read_state().get("state")
    owners = {
        side: _active_owner(state, captured_session_id, side)
        for side in ("self", "opponent")
    }
    if owners.get(checked["actor"]["side"]) != checked["actor"] or owners.get(affected["side"]) != affected:
        return _result("rejected", "causal_action_owner_not_current")
    if not all(isinstance(owner, dict) for owner in owners.values()):
        return _result("rejected", "active_owner_snapshot_incomplete")

    payload = {
        "producer_source_action_id": producer_action_id,
        "producer_move_id": checked["move_id"],
        "producer_owner": deepcopy(checked["actor"]),
        "producer_execution_observation_id": producer_execution_observation["observation_id"],
        "affected_owner": deepcopy(affected),
        "cancelled_source_action_id": cancelled_action_id,
        "cancelled_move_id": cancelled_move_id,
        "cancelled_execution_observation_id": cancelled_execution_observation["observation_id"],
        "cancelled_result_observation_id": cancelled_result_observation["observation_id"],
        "producer_predictive_ledger_fingerprint": checked["predictive_ledger_fingerprint"],
    }
    boundary = LifecycleConfirmationBoundary(captured_session_id, owners)
    confirmation = boundary.confirm(
        event_kind="flinch_causality_observed",
        payload=payload,
        session_id=captured_session_id,
        source=FLINCH_CAUSALITY_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=checked["actor"]["side"],
        slot_index=checked["actor"]["slot_index"],
        pokemon_id=checked["actor"]["pokemon_id"],
        observation_id=f"{captured_session_id}:flinch-causality:{sequence}",
        turn_number=checked["turn_number"],
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "flinch_causality_confirmation_rejected"))
    observation = deepcopy(confirmation["observation"])
    observation["observation_sequence"] = sequence
    observation.update(
        producer_source_action_id=producer_action_id,
        producer_move_id=checked["move_id"],
        producer_owner=deepcopy(checked["actor"]),
        producer_execution_observation_id=producer_execution_observation["observation_id"],
        affected_owner=deepcopy(affected),
        cancelled_source_action_id=cancelled_action_id,
        cancelled_move_id=cancelled_move_id,
        cancelled_execution_observation_id=cancelled_execution_observation["observation_id"],
        cancelled_result_observation_id=cancelled_result_observation["observation_id"],
        producer_predictive_ledger_fingerprint=checked["predictive_ledger_fingerprint"],
        reconciliation_eligible=True,
        provenance=PROVENANCE,
    )
    confirmation = {**deepcopy(confirmation), "observation": observation}

    admitted = runtime_session_manager.admit_confirmation(captured_session_id, confirmation)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "flinch_causality_observation_admission_rejected")
    return {
        "status": "resolved",
        "observation": deepcopy(observation),
        "runtime_committed": False,
        "provenance": PROVENANCE,
    }


def _validate_producer_execution(value: Any, binding: Mapping[str, Any]) -> str | None:
    if not isinstance(value, Mapping) or value.get("event_kind") != "executed_move_observed":
        return "producer_execution_observation_invalid"
    if value.get("session_id") != binding["session_id"] or value.get("turn_number") != binding["turn_number"]:
        return "producer_execution_session_or_turn_mismatch"
    if _owner_from_observation(value) != binding["actor"]:
        return "producer_execution_owner_mismatch"
    payload = _payload(value)
    if payload.get("source_action_id") != binding["source_action_id"] or payload.get("move_id") != binding["move_id"]:
        return "producer_execution_action_link_mismatch"
    return None


def _validate_cancelled_history(
    execution: Any, result: Any, *, affected: Mapping[str, Any], session_id: str, turn_number: int,
) -> str | None:
    if not isinstance(execution, Mapping) or execution.get("event_kind") != "executed_move_observed":
        return "cancelled_execution_observation_invalid"
    if execution.get("session_id") != session_id or execution.get("turn_number") != turn_number:
        return "cancelled_execution_session_or_turn_mismatch"
    if _owner_from_observation(execution) != affected:
        return "cancelled_execution_actor_mismatch"
    ep = _payload(execution)
    action_id, move_id = ep.get("source_action_id"), ep.get("move_id")
    if not isinstance(action_id, str) or not action_id or not isinstance(move_id, str) or not move_id:
        return "cancelled_execution_action_invalid"

    if not isinstance(result, Mapping) or result.get("event_kind") != "previous_action_result_observed":
        return "cancelled_result_observation_invalid"
    if result.get("session_id") != session_id or result.get("turn_number") != turn_number:
        return "cancelled_result_session_or_turn_mismatch"
    if _owner_from_observation(result) != affected:
        return "cancelled_result_actor_mismatch"
    rp = _payload(result)
    if (
        rp.get("previous_action_id") != action_id
        or rp.get("execution_move_id") != move_id
        or rp.get("selected_move_id") != move_id
        or rp.get("result_class") != "flinch"
    ):
        return "cancelled_result_action_or_class_mismatch"
    if result.get("related_observation_id") != execution.get("observation_id"):
        return "cancelled_result_execution_reference_mismatch"
    if _sequence(result) <= _sequence(execution):
        return "cancelled_result_sequence_invalid"
    return None


def _execution_matches(rows, owner, action_id, move_id, turn_number):
    return [
        row for row in rows
        if row.get("event_kind") == "executed_move_observed"
        and row.get("turn_number") == turn_number
        and _owner_from_observation(row) == owner
        and _payload(row).get("source_action_id") == action_id
        and _payload(row).get("move_id") == move_id
    ]


def _active_owner(state: Any, session_id: str, side: str):
    if not isinstance(state, Mapping) or side not in {"self", "opponent"}:
        return None
    side_state = state.get(f"{side}_side")
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    row = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) and not isinstance(slot, bool) else None
    pokemon_id = row.get("pokemon_id") if isinstance(row, Mapping) else None
    if not isinstance(pokemon_id, str) or not pokemon_id:
        return None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}


def _owner_from_observation(value: Mapping[str, Any]):
    return {
        "session_id": value.get("session_id"),
        "side": value.get("side"),
        "slot_index": value.get("slot_index"),
        "pokemon_id": value.get("pokemon_id"),
    }


def _payload(value: Mapping[str, Any]):
    payload = value.get("payload")
    return payload if isinstance(payload, Mapping) else value


def _sequence(value: Mapping[str, Any]) -> int:
    value = value.get("observation_sequence")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason, "observation": None, "runtime_committed": False}
