"""Strict derived lifecycle records for observed sleep/freeze actions.

These records are deliberately not a status mutation API.  They can only
follow one user-confirmed pending-status action result in the same replay
batch; replay and the reducer repeat that binding check.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

MECHANICS_DERIVED_TRUST = "mechanics_derived_runtime"
CHAMPIONS_STATUS_ACTION_LIFECYCLE_SOURCE = "runtime_champions_status_action_lifecycle_v1"
PROGRESSION_DERIVED = "champions_status_progression_derived"
CONDITION_CLEARED_DERIVED = "champions_status_condition_cleared_derived"
DERIVED_KINDS = frozenset({PROGRESSION_DERIVED, CONDITION_CLEARED_DERIVED})


def derive_status_action_lifecycle_consequence(*, event_kind: str, session_id: str,
                                                turn_number: int, observation_id: str,
                                                observation_sequence: int,
                                                source_pending_observation: Mapping[str, Any],
                                                payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build one collection-facing, source-bound lifecycle consequence."""
    source = dict(source_pending_observation) if isinstance(source_pending_observation, Mapping) else {}
    data = deepcopy(dict(payload)) if isinstance(payload, Mapping) else {}
    if (event_kind not in DERIVED_KINDS or not _positive(turn_number) or not _positive(observation_sequence)
            or not isinstance(observation_id, str) or not observation_id
            or source.get("event_kind") != "pending_status_action_execution_observed"
            or source.get("session_id") != session_id or source.get("turn_number") != turn_number
            or not isinstance(source.get("observation_id"), str) or not source["observation_id"]
            or not _positive(source.get("observation_sequence"))
            or source["observation_sequence"] >= observation_sequence):
        return _bad("invalid_pending_status_action_source")
    data["source_pending_observation_id"] = source["observation_id"]
    if not _valid(event_kind, source, data):
        return _bad("invalid_champions_status_lifecycle_payload")
    return {"status": "confirmed", "observation": {
        "event_kind": event_kind, "session_id": session_id, "turn_number": turn_number,
        "observation_id": observation_id, "observation_sequence": observation_sequence,
        "side": source.get("side"), "slot_index": source.get("slot_index"),
        "pokemon_id": source.get("pokemon_id"), "payload": data,
        "source": CHAMPIONS_STATUS_ACTION_LIFECYCLE_SOURCE,
        "trust": MECHANICS_DERIVED_TRUST, "scope": "champions_status_action_lifecycle",
        "reducer_eligibility": "candidate",
    }}


def _valid(kind: str, source: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    source_payload = source.get("payload")
    if not isinstance(source_payload, Mapping):
        return False
    required = ("decision_point", "action_id", "move_id", "condition", "outcome_class")
    if any(payload.get(key) != source_payload.get(key) for key in required):
        return False
    condition, outcome = payload.get("condition"), payload.get("outcome_class")
    if condition not in {"sleep", "freeze"}:
        return False
    if kind == PROGRESSION_DERIVED:
        return (outcome in {"blocked_sleep", "blocked_freeze"}
                and ((condition == "sleep" and outcome == "blocked_sleep") or (condition == "freeze" and outcome == "blocked_freeze"))
                and isinstance(payload.get("prior_attempts_before"), int)
                and payload.get("prior_attempts_after") == payload["prior_attempts_before"] + 1)
    return (outcome in {"wake_and_execute", "natural_thaw_and_execute", "self_thaw_move_execute"}
            and ((condition == "sleep" and outcome == "wake_and_execute")
                 or (condition == "freeze" and outcome in {"natural_thaw_and_execute", "self_thaw_move_execute"})))


def _positive(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _bad(reason: str) -> dict[str, Any]:
    return {"status": "rejected", "reason": reason, "observation": None}
