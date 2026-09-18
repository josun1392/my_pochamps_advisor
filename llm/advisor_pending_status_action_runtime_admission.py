"""Production admission for one observed sleep/freeze pending action outcome."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_champions_status_action_lifecycle_derived_observation import (
    CONDITION_CLEARED_DERIVED, PROGRESSION_DERIVED,
    derive_status_action_lifecycle_consequence,
)
from llm.advisor_champions_status_progression import valid_progression
from llm.advisor_lifecycle_confirmation import (
    LifecycleConfirmationBoundary, PENDING_STATUS_ACTION_EXECUTION_SOURCE, USER_TRUST,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def admit_pending_status_action_execution(*, runtime_session_manager: BattleObservationRuntimeSessionManager,
                                          captured_session_id: str, side: str, slot_index: int,
                                          pokemon_id: str, turn_number: int, decision_point: str,
                                          action_id: str, move_id: str, condition: str,
                                          execution_state: str, blocker: str | None,
                                          outcome_class: str) -> dict[str, Any]:
    """Atomically admit the actual result and only its deterministic lifecycle.

    This boundary never consults the predictive gate.  ``outcome_class`` is an
    explicit user-confirmed fact and is validated by lifecycle confirmation.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    state = snapshot.get("state") if snapshot.get("status") == "runtime_snapshot_ready" else None
    owner, pokemon = _active_owner(state, side)
    if owner is None or owner.get("slot_index") != slot_index or owner.get("pokemon_id") != pokemon_id:
        return _result("rejected", "pending_status_action_actor_mismatch")
    duplicate = state.get("pending_status_action_execution_context") if isinstance(state, Mapping) else None
    if _same_pending_action_identity(duplicate, owner, decision_point, action_id, move_id, condition) and not _same_semantic_pending_action(
        duplicate, owner, decision_point, action_id, move_id, condition, execution_state, blocker, outcome_class
    ):
        return _result("rejected", "conflicting_pending_status_action_retry")
    if _same_semantic_pending_action(duplicate, owner, decision_point, action_id, move_id, condition, execution_state, blocker, outcome_class):
        if not _pending_context_is_current(state, duplicate):
            return _result("rejected", "stale_pending_status_action_duplicate")
        committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=owner) if committed.get("status") == "runtime_snapshot_ready" else {}
        return {"status": "resolved", "reason": "duplicate_pending_status_action", "runtime_committed": False,
                "observation": None, "derived_observations": [], "runtime_snapshot": deepcopy(committed),
                "strategy_d0": d0 if d0.get("status") == "resolved" else None}
    if pokemon.get("condition") != condition:
        return _result("rejected", "pending_status_action_condition_mismatch")
    sequence = runtime_session_manager.allocate_observation_sequence()
    if sequence.get("status") != "allocated" or sequence.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    source_seq = sequence["observation_sequence"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, {side: owner}).confirm(
        event_kind="pending_status_action_execution_observed",
        payload={"decision_point": decision_point, "action_id": action_id, "move_id": move_id,
                 "condition": condition, "execution_state": execution_state, "blocker": blocker,
                 "outcome_class": outcome_class},
        session_id=captured_session_id, source=PENDING_STATUS_ACTION_EXECUTION_SOURCE, trust=USER_TRUST,
        confirmed=True, side=side, slot_index=slot_index, pokemon_id=pokemon_id,
        observation_id=f"{captured_session_id}:pending-status-action:{source_seq}", turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "pending_status_action_confirmation_rejected"))
    source = confirmation["observation"]
    source["observation_sequence"] = source_seq
    derived = _derive(state, pokemon, source, runtime_session_manager.allocate_observation_sequence)
    if derived.get("status") != "resolved":
        return _result(derived.get("status", "incomplete"), derived.get("reason", "status_lifecycle_authority_incomplete"))
    confirmations = [confirmation, *derived["confirmations"]]
    observations = [row["observation"] for row in confirmations]
    preview_snapshot = _preview_snapshot(runtime_session_manager.read_collection_snapshot(), observations)
    preview = runtime_session_manager.preview(captured_session_id, preview_snapshot) if preview_snapshot else {}
    if preview.get("status") != "preview_ready":
        return _result("rejected", "status_lifecycle_preview_rejected")
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, confirmations)
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "status_lifecycle_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "status_lifecycle_application_rejected")
    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if committed.get("status") != "runtime_snapshot_ready":
        return {**_result("resolved", None), "runtime_committed": True, "post_commit_verification_failure": "runtime_snapshot_unavailable"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=owner)
    return {"status": "resolved", "reason": None, "runtime_committed": True,
            "observation": deepcopy(source), "derived_observations": deepcopy(observations[1:]),
            "runtime_snapshot": deepcopy(committed), "strategy_d0": d0 if d0.get("status") == "resolved" else None,
            "post_commit_verification_failure": None if d0.get("status") == "resolved" else "committed_runtime_d0_unavailable"}


def _derive(state: Mapping[str, Any], pokemon: Mapping[str, Any], source: Mapping[str, Any], allocate) -> dict[str, Any]:
    payload = source["payload"]
    outcome = payload["outcome_class"]
    owner = {"session_id": state.get("session_id"), "side": source.get("side"), "slot_index": source.get("slot_index"), "pokemon_id": source.get("pokemon_id")}
    row = pokemon.get("champions_status_progression")
    if not valid_progression(row, owner) or row.get("condition") != payload["condition"]:
        return {"status": "incomplete", "reason": "champions_status_progression_unavailable"}
    current_condition_observation = pokemon.get("condition_provenance")
    if (
        not isinstance(current_condition_observation, Mapping)
        or current_condition_observation.get("event_kind") != "current_condition_observed"
        or current_condition_observation.get("trust") != "user_confirmed_observation"
        or current_condition_observation.get("condition") != payload["condition"]
        or row.get("condition_observation") != current_condition_observation
    ):
        return {"status": "rejected", "reason": "champions_status_progression_foreign_or_stale"}
    if outcome == "sleep_exception_execute":
        return {"status": "resolved", "confirmations": []}
    allocated = allocate()
    if allocated.get("status") != "allocated":
        return {"status": "rejected", "reason": "derived_sequence_unavailable"}
    common = {key: payload[key] for key in ("decision_point", "action_id", "move_id", "condition", "outcome_class")}
    if outcome in {"blocked_sleep", "blocked_freeze"}:
        next_attempt = row["prior_attempts"] + 1
        if (next_attempt > 2 or (payload["condition"] == "sleep" and isinstance(row.get("sleep_duration"), int) and next_attempt >= row["sleep_duration"])):
            return {"status": "rejected", "reason": "blocked_status_outcome_contradicts_progression"}
        common.update(prior_attempts_before=row["prior_attempts"], prior_attempts_after=row["prior_attempts"] + 1)
        kind = PROGRESSION_DERIVED
    else:
        kind = CONDITION_CLEARED_DERIVED
    result = derive_status_action_lifecycle_consequence(
        event_kind=kind, session_id=state.get("session_id"), turn_number=source["turn_number"],
        observation_id=f"{state.get('session_id')}:status-lifecycle:{allocated['observation_sequence']}",
        observation_sequence=allocated["observation_sequence"], source_pending_observation=source, payload=common)
    return {"status": "resolved", "confirmations": [result]} if result.get("status") == "confirmed" else {"status": "rejected", "reason": result.get("reason")}


def _active_owner(state: Any, side: str):
    side_state = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = side_state.get("pokemon") if isinstance(side_state, Mapping) else None
    slot = side_state.get("active_slot_index") if isinstance(side_state, Mapping) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) else None
    if not isinstance(pokemon, Mapping) or not isinstance(state.get("session_id"), str):
        return None, None
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": pokemon.get("pokemon_id")}, pokemon


def _preview_snapshot(snapshot: Mapping[str, Any], observations: list[Mapping[str, Any]]):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready": return None
    rows = deepcopy(snapshot.get("ordered_observations", [])); rows.extend(deepcopy(dict(row)) for row in observations)
    rows.sort(key=lambda row: (row.get("observation_sequence"), row.get("observation_id")))
    return {**deepcopy(dict(snapshot)), "ordered_observations": rows}


def _result(status: str, reason: str | None):
    return {"status": status, "reason": reason, "runtime_committed": False, "observation": None,
            "derived_observations": [], "runtime_snapshot": None, "strategy_d0": None}


def _same_pending_action_identity(context: Any, owner: Mapping[str, Any], decision_point: str,
                                  action_id: str, move_id: str, condition: str) -> bool:
    return isinstance(context, Mapping) and context.get("actor") == dict(owner) and all(
        context.get(key) == value for key, value in {
            "decision_point": decision_point, "action_id": action_id, "move_id": move_id, "condition": condition,
        }.items())


def _same_semantic_pending_action(context: Any, owner: Mapping[str, Any], decision_point: str, action_id: str,
                                  move_id: str, condition: str, execution_state: str, blocker: str | None,
                                  outcome_class: str) -> bool:
    return isinstance(context, Mapping) and context.get("actor") == dict(owner) and all(
        context.get(key) == value for key, value in {
            "decision_point": decision_point, "action_id": action_id, "move_id": move_id,
            "condition": condition, "execution_state": execution_state, "blocker": blocker,
            "outcome_class": outcome_class,
        }.items())


def _pending_context_is_current(state: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    last = state.get("last_applied_observation_sequence")
    provenance = context.get("provenance") if isinstance(context, Mapping) else None
    source_sequence = provenance.get("source_sequence") if isinstance(provenance, Mapping) else None
    if not isinstance(last, int) or isinstance(last, bool) or not isinstance(source_sequence, int) or isinstance(source_sequence, bool):
        return False
    if last == source_sequence:
        return True
    return (
        context.get("lifecycle_batch_terminal_sequence") == last
        and context.get("lifecycle_batch_source_observation_id") == provenance.get("source_observation_id")
    )
