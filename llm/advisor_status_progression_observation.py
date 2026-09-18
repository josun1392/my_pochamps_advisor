"""Production admission for one explicit current sleep/freeze progression fact."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_champions_status_progression import valid_progression
from llm.advisor_lifecycle_confirmation import (
    STATUS_PROGRESSION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def admit_champions_status_progression_observation(
    *,
    runtime_session_manager: BattleObservationRuntimeSessionManager,
    captured_session_id: str,
    side: str,
    established_turn: int,
    prior_attempts: int,
    sleep_duration: int | None,
    turn_number: int,
) -> dict[str, Any]:
    """Commit explicitly known sleep/freeze progression for the current active owner.

    The current runtime condition observation owns the episode identity.  Merely
    observing sleep/freeze never creates progression authority.
    """
    if not isinstance(runtime_session_manager, BattleObservationRuntimeSessionManager):
        return _result("rejected", "invalid_runtime_manager")
    if not isinstance(captured_session_id, str) or not captured_session_id:
        return _result("rejected", "invalid_session")
    if side not in {"self", "opponent"}:
        return _result("rejected", "invalid_status_progression_side")
    if not _positive(established_turn) or not _attempts(prior_attempts) or not _duration(sleep_duration) or not _positive(turn_number):
        return _result("rejected", "invalid_status_progression_request")

    snapshot = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    if snapshot.get("status") != "runtime_snapshot_ready":
        return _result("rejected" if snapshot.get("status") == "stale_session" else "incomplete", "runtime_snapshot_unavailable")
    owner, pokemon = _active_owner(snapshot.get("state"), captured_session_id, side)
    if owner is None or pokemon is None:
        return _result("rejected", "status_progression_owner_unavailable")

    condition = pokemon.get("condition")
    provenance = pokemon.get("condition_provenance")
    if not isinstance(condition, str) or condition not in {"sleep", "freeze"}:
        if _unknown(condition) or condition is None:
            return _result("incomplete", "current_sleep_freeze_condition_unavailable")
        return _result("rejected", "current_condition_not_sleep_or_freeze")
    if not _valid_condition_provenance(provenance, condition):
        return _result("rejected", "current_sleep_freeze_condition_provenance_invalid")
    if condition == "freeze" and sleep_duration is not None:
        return _result("rejected", "freeze_sleep_duration_must_be_none")
    if turn_number < max(established_turn, provenance["turn_number"]):
        return _result("rejected", "status_progression_turn_precedes_episode")

    origin_id = _origin_id(provenance["source_observation_id"])
    payload = {
        "condition": condition,
        "origin_id": origin_id,
        "established_turn": established_turn,
        "prior_attempts": prior_attempts,
        "sleep_duration": sleep_duration,
    }

    prior = pokemon.get("champions_status_progression")
    if isinstance(prior, Mapping) and prior.get("condition_observation") == provenance:
        if not valid_progression(prior, owner):
            return _result("rejected", "invalid_prior_champions_status_progression")
        conflict = _same_episode_conflict(prior, payload)
        if conflict is not None:
            return _result("rejected", conflict)
        if _same_progression(prior, payload):
            historical = _matching_observation(
                runtime_session_manager.read_collection_snapshot(),
                session_id=captured_session_id,
                owner=owner,
                payload=payload,
            )
            if historical is None:
                return _result("rejected", "status_progression_history_unavailable")
            fresh = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
            if fresh.get("status") != "resolved":
                return _result("rejected", "committed_runtime_d0_unavailable")
            return {
                "status": "resolved",
                "reason": "idempotent_reuse",
                "owner": deepcopy(owner),
                "condition": condition,
                "origin_id": origin_id,
                "observation": deepcopy(historical),
                "runtime_snapshot": deepcopy(snapshot),
                "strategy_d0": fresh,
                "progression": deepcopy(dict(prior)),
                "runtime_committed": False,
                "idempotent": True,
            }

    allocated = runtime_session_manager.allocate_observation_sequence()
    if allocated.get("status") != "allocated" or allocated.get("session_id") != captured_session_id:
        return _result("rejected", "observation_sequence_binding_mismatch")
    sequence = allocated["observation_sequence"]
    confirmation = LifecycleConfirmationBoundary(captured_session_id, {side: owner}).confirm(
        event_kind="champions_status_progression_observed",
        payload=payload,
        session_id=captured_session_id,
        source=STATUS_PROGRESSION_SOURCE,
        trust=USER_TRUST,
        confirmed=True,
        side=side,
        slot_index=owner["slot_index"],
        pokemon_id=owner["pokemon_id"],
        observation_id=f"{captured_session_id}:status-progression:{sequence}",
        turn_number=turn_number,
    )
    if confirmation.get("status") != "confirmed":
        return _result("rejected", confirmation.get("excluded_reason", "status_progression_confirmation_rejected"))
    observation = confirmation["observation"]
    observation["observation_sequence"] = sequence

    collection = runtime_session_manager.read_collection_snapshot()
    preview = _preview_snapshot(collection, [observation])
    if preview is None or runtime_session_manager.preview(captured_session_id, preview).get("status") != "preview_ready":
        return _result("rejected", "status_progression_preview_rejected")
    admitted = runtime_session_manager.admit_confirmations_atomically(captured_session_id, [confirmation])
    if admitted.get("status") not in {"added", "duplicate"}:
        return _result("rejected", "status_progression_admission_rejected")
    applied = runtime_session_manager.apply(captured_session_id, runtime_session_manager.read_collection_snapshot())
    if applied.get("status") not in {"applied", "already_applied"}:
        return _result("rejected", "status_progression_application_rejected")

    committed = runtime_session_manager.capture_runtime_state_snapshot(captured_session_id)
    committed_owner, committed_pokemon = _active_owner(committed.get("state"), captured_session_id, side)
    progression = committed_pokemon.get("champions_status_progression") if isinstance(committed_pokemon, Mapping) else None
    if (
        committed.get("status") != "runtime_snapshot_ready"
        or committed_owner != owner
        or not valid_progression(progression, owner)
        or progression.get("condition") != condition
        or progression.get("origin_id") != origin_id
        or progression.get("established_turn") != established_turn
        or progression.get("prior_attempts") != prior_attempts
        or progression.get("sleep_duration") != sleep_duration
        or progression.get("condition_observation") != provenance
    ):
        return _result("rejected", "committed_status_progression_verification_failed")
    fresh = freeze_runtime_strategy_d0(runtime_snapshot=committed, decision_owner=owner)
    if (
        fresh.get("status") != "resolved"
        or fresh.get("source_runtime_fingerprint") != committed.get("state_fingerprint")
        or fresh.get("source_runtime_fingerprint") == snapshot.get("state_fingerprint")
    ):
        return _result("rejected", "status_progression_fresh_d0_verification_failed")
    return {
        "status": "resolved",
        "reason": None,
        "owner": deepcopy(owner),
        "condition": condition,
        "origin_id": origin_id,
        "observation": deepcopy(observation),
        "runtime_snapshot": deepcopy(committed),
        "strategy_d0": fresh,
        "progression": deepcopy(dict(progression)),
        "runtime_committed": True,
        "idempotent": False,
    }


def _active_owner(state: Any, session_id: str, side: str):
    container = state.get(f"{side}_side") if isinstance(state, Mapping) else None
    roster = container.get("pokemon") if isinstance(container, Mapping) else None
    slot = container.get("active_slot_index") if isinstance(container, Mapping) else None
    pokemon = roster.get(slot, roster.get(str(slot))) if isinstance(roster, Mapping) and isinstance(slot, int) and not isinstance(slot, bool) else None
    pokemon_id = pokemon.get("pokemon_id") if isinstance(pokemon, Mapping) else None
    if (
        not isinstance(state, Mapping) or state.get("session_id") != session_id
        or not isinstance(slot, int) or isinstance(slot, bool) or slot < 0
        or not isinstance(pokemon_id, str) or not pokemon_id
        or pokemon.get("fainted") is True
    ):
        return None, None
    return {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": pokemon_id}, pokemon


def _valid_condition_provenance(value: Any, condition: str) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("event_kind") == "current_condition_observed"
        and value.get("trust") == USER_TRUST
        and value.get("condition") == condition
        and isinstance(value.get("source_observation_id"), str) and bool(value["source_observation_id"])
        and isinstance(value.get("source_sequence"), int) and not isinstance(value["source_sequence"], bool) and value["source_sequence"] >= 1
        and isinstance(value.get("turn_number"), int) and not isinstance(value["turn_number"], bool) and value["turn_number"] >= 1
    )


def _origin_id(condition_observation_id: str) -> str:
    return f"{condition_observation_id}:sleep-freeze-episode"


def _same_episode_conflict(prior: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    if prior.get("origin_id") != payload.get("origin_id"):
        return "status_progression_origin_mismatch"
    if prior.get("established_turn") != payload.get("established_turn"):
        return "status_progression_established_turn_conflict"
    if payload["prior_attempts"] < prior.get("prior_attempts", -1):
        return "stale_champions_status_progression"
    if prior.get("sleep_duration") is not None and payload.get("sleep_duration") != prior.get("sleep_duration"):
        return "champions_sleep_duration_reroll_rejected"
    return None


def _same_progression(prior: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    return all(prior.get(key) == payload.get(key) for key in ("condition", "origin_id", "established_turn", "prior_attempts", "sleep_duration"))


def _matching_observation(snapshot: Any, *, session_id: str, owner: Mapping[str, Any], payload: Mapping[str, Any]):
    rows = snapshot.get("ordered_observations") if isinstance(snapshot, Mapping) and snapshot.get("status") == "ready" else None
    if not isinstance(rows, list):
        return None
    matches = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("event_kind") == "champions_status_progression_observed"
        and row.get("session_id") == session_id
        and row.get("source") == STATUS_PROGRESSION_SOURCE
        and row.get("trust") == USER_TRUST
        and (row.get("side"), row.get("slot_index"), row.get("pokemon_id")) == (owner["side"], owner["slot_index"], owner["pokemon_id"])
        and row.get("payload") == dict(payload)
    ]
    return matches[-1] if len(matches) == 1 else None


def _preview_snapshot(snapshot: Any, observations: list[Mapping[str, Any]]):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready" or not isinstance(snapshot.get("ordered_observations"), list):
        return None
    rows = deepcopy(snapshot["ordered_observations"])
    rows.extend(deepcopy(dict(row)) for row in observations)
    rows.sort(key=lambda row: (row.get("observation_sequence"), row.get("observation_id")))
    return {**deepcopy(dict(snapshot)), "ordered_observations": rows}


def _unknown(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("knowledge") == "unknown"


def _positive(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _attempts(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2


def _duration(value: Any) -> bool:
    return value is None or type(value) is int and value in {2, 3}


def _result(status: str, reason: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "owner": None,
        "condition": None,
        "origin_id": None,
        "observation": None,
        "runtime_snapshot": None,
        "strategy_d0": None,
        "progression": None,
        "runtime_committed": False,
        "idempotent": False,
    }
