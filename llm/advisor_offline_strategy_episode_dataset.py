"""Detached, reward-free episodes over authenticated offline transition records."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_strategy_transition_replay import SCHEMA_VERSION as TRANSITION_SCHEMA


EPISODE_SCHEMA_VERSION = "offline-strategy-episode-v1"
DATASET_SCHEMA_VERSION = "offline-strategy-dataset-v1"


def materialize_offline_strategy_episode(transitions: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Order validated transitions and prove each adjacent decision-state link."""
    if not isinstance(transitions, (tuple, list)) or not transitions:
        return _failure(EPISODE_SCHEMA_VERSION, "transitions_invalid")
    try:
        if any(not _transition_surface(row) for row in transitions):
            return _failure(EPISODE_SCHEMA_VERSION, "transition_invalid_or_incomplete")
    except (KeyError, TypeError, ValueError, OverflowError):
        return _failure(EPISODE_SCHEMA_VERSION, "transition_invalid_or_incomplete")
    ordered = sorted(transitions, key=_order_key)
    session = ordered[0]["decision_provenance"]["session_id"]
    if any(row["decision_provenance"]["session_id"] != session for row in ordered):
        return _failure(EPISODE_SCHEMA_VERSION, "mixed_session")
    if any(row["decision_provenance"]["decision_owner"]["side"] != "self" for row in ordered):
        return _failure(EPISODE_SCHEMA_VERSION, "foreign_decision_side")
    ids = [row["transition_id"] for row in ordered]
    observations = [row["executed_action"]["observation_id"] for row in ordered]
    decisions = [_decision_key(row) for row in ordered]
    if len(set(ids)) != len(ids):
        return _failure(EPISODE_SCHEMA_VERSION, "duplicate_transition_id")
    if len(set(observations)) != len(observations):
        return _failure(EPISODE_SCHEMA_VERSION, "duplicate_executed_observation")
    if len(set(decisions)) != len(decisions):
        return _failure(EPISODE_SCHEMA_VERSION, "conflicting_decision_provenance")
    gaps = []
    for index, (previous, current) in enumerate(zip(ordered, ordered[1:]), start=1):
        prior_next = previous["next_state"]
        decision = current["decision_provenance"]
        prior_sequence = prior_next["last_applied_observation_sequence"]
        decision_sequence = decision["last_applied_observation_sequence"]
        if (
            _order_key(previous) >= _order_key(current)
            or decision_sequence < prior_sequence
            or current["executed_action"]["observation_sequence"] <= prior_sequence
            or decision["turn_number"] < prior_next["turn_number"]
        ):
            return _failure(EPISODE_SCHEMA_VERSION, "overlapping_temporal_windows")
        same_state = prior_next["state_fingerprint"] == decision["source_runtime_fingerprint"]
        if decision_sequence == prior_sequence:
            if not same_state:
                return _failure(EPISODE_SCHEMA_VERSION, "broken_state_continuity")
            active = prior_next["observed_summary"]["decision_side_active_owner"]
            if active["availability"] != "available":
                gaps.append(index)
            elif active["value"] != decision["decision_owner"]:
                return _failure(EPISODE_SCHEMA_VERSION, "foreign_owner_lineage")
        elif same_state:
            return _failure(EPISODE_SCHEMA_VERSION, "state_sequence_fingerprint_conflict")
        else:
            # A later decision may be valid, but the intervening reducer chain is absent.
            gaps.append(index)
    identity = {
        "session_id": session, "transition_ids": ids,
        "first_decision": _plain(ordered[0]["decision_provenance"]),
        "final_next_state": _next_provenance(ordered[-1]["next_state"]),
    }
    episode_id = "offline-episode:" + hashlib.sha256(_canonical(identity)).hexdigest()
    terminal = ordered[-1]["next_state"]["observed_summary"]["battle_terminal"]
    return _freeze({
        "status": "incomplete" if gaps else "resolved",
        "schema_version": EPISODE_SCHEMA_VERSION,
        "episode_id": episode_id, "session_id": session,
        "completeness": "intermediate_state_lineage_unavailable" if gaps else "strict_observed_chain",
        "continuity_gaps": tuple(gaps), "transition_ids": tuple(ids),
        "transitions": tuple(ordered), "terminal_status": terminal,
        "first_decision": ordered[0]["decision_provenance"],
        "final_next_state": _next_provenance(ordered[-1]["next_state"]),
    })


def materialize_offline_strategy_dataset(episodes: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Collect resolved, session-isolated episodes without persistence or sampling."""
    if not isinstance(episodes, (tuple, list)) or not episodes:
        return _failure(DATASET_SCHEMA_VERSION, "episodes_invalid")
    if any(not isinstance(item, MappingProxyType) or item.get("schema_version") != EPISODE_SCHEMA_VERSION for item in episodes):
        return _failure(DATASET_SCHEMA_VERSION, "episode_schema_invalid")
    if any(item.get("status") != "resolved" for item in episodes):
        return _failure(DATASET_SCHEMA_VERSION, "episode_incomplete")
    # Rebuild from their transition records, so dataset input cannot change episode identity.
    rebuilt = [materialize_offline_strategy_episode(item.get("transitions")) for item in episodes]
    if any(item["status"] != "resolved" for item in rebuilt):
        return _failure(DATASET_SCHEMA_VERSION, "episode_revalidation_failed")
    if any(supplied != checked for supplied, checked in zip(episodes, rebuilt)):
        return _failure(DATASET_SCHEMA_VERSION, "episode_identity_mismatch")
    ordered = sorted(rebuilt, key=lambda item: (item["session_id"], item["episode_id"]))
    ids = [item["episode_id"] for item in ordered]
    sessions = [item["session_id"] for item in ordered]
    transitions = [transition_id for item in ordered for transition_id in item["transition_ids"]]
    if len(set(ids)) != len(ids):
        return _failure(DATASET_SCHEMA_VERSION, "duplicate_episode_id")
    if len(set(transitions)) != len(transitions):
        return _failure(DATASET_SCHEMA_VERSION, "duplicate_transition_across_episodes")
    if len(set(sessions)) != len(sessions):
        return _failure(DATASET_SCHEMA_VERSION, "session_not_isolated")
    dataset_id = "offline-dataset:" + hashlib.sha256(_canonical(ids)).hexdigest()
    return _freeze({
        "status": "resolved", "schema_version": DATASET_SCHEMA_VERSION,
        "dataset_id": dataset_id, "episode_ids": tuple(ids), "episodes": tuple(ordered),
    })


def _transition_surface(row: Any) -> bool:
    # V1 is an in-memory contract over the upstream detached materializer result.
    if not isinstance(row, MappingProxyType) or row.get("schema_version") != TRANSITION_SCHEMA or row.get("status") != "resolved" or row.get("completeness") != "strict_observed_transition":
        return False
    decision, action, next_state, feature = (row.get(key) for key in ("decision_provenance", "executed_action", "next_state", "decision_feature_row"))
    if not all(isinstance(item, Mapping) for item in (decision, action, next_state, feature)):
        return False
    session, owner = decision.get("session_id"), decision.get("decision_owner")
    summary = next_state.get("observed_summary")
    if not isinstance(session, str) or not session or not isinstance(owner, Mapping) or not isinstance(summary, Mapping):
        return False
    if any(key not in next_state for key in ("session_id", "state_fingerprint", "last_applied_observation_sequence", "observation_id", "turn_number")):
        return False
    active, terminal = summary.get("decision_side_active_owner"), summary.get("battle_terminal")
    if not isinstance(active, Mapping) or not isinstance(terminal, Mapping):
        return False
    if active.get("availability") not in {"available", "unavailable"} or (active.get("availability") == "available" and not isinstance(active.get("value"), Mapping)):
        return False
    # The current transition authority has no strict battle-terminal producer.
    if terminal != {"availability": "unavailable", "reason": "battle_terminality_not_observed"}:
        return False
    if not isinstance(row.get("transition_id"), str) or not row["transition_id"].startswith("offline-transition:"):
        return False
    if any(not _digest(value) for value in (decision.get("source_runtime_fingerprint"), decision.get("source_branch_fingerprint"), next_state.get("state_fingerprint"))):
        return False
    if any(not _sequence(value, zero=zero) for value, zero in (
        (decision.get("last_applied_observation_sequence"), True),
        (action.get("observation_sequence"), False),
        (next_state.get("last_applied_observation_sequence"), False),
        (decision.get("turn_number"), False), (action.get("turn_number"), False), (next_state.get("turn_number"), False),
    )):
        return False
    if not (decision["last_applied_observation_sequence"] < action["observation_sequence"] <= next_state["last_applied_observation_sequence"]):
        return False
    if not (decision["turn_number"] == action["turn_number"] <= next_state["turn_number"]):
        return False
    if owner.get("session_id") != session or owner.get("side") not in {"self", "opponent"} or action.get("actor") != owner or next_state.get("session_id") != session:
        return False
    # The feature row predates decision turn/sequence; compare its original binding.
    expected = {key: decision.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    if feature.get("candidate_id") != action.get("candidate_id") or feature.get("action_type") != action.get("action_type") or feature.get("provenance") != {**expected, "candidate_id": action.get("candidate_id")}:
        return False
    if not isinstance(action.get("observation_id"), str) or not action["observation_id"] or not isinstance(next_state.get("observation_id"), str) or not next_state["observation_id"]:
        return False
    identity = {"decision": decision, "action": action, "next_state": _next_provenance(next_state), "feature_row": feature}
    return row["transition_id"] == "offline-transition:" + hashlib.sha256(_canonical(identity)).hexdigest()


def _order_key(row: Mapping[str, Any]) -> tuple[int, int, int]:
    return (row["decision_provenance"]["turn_number"], row["executed_action"]["observation_sequence"], row["next_state"]["last_applied_observation_sequence"])


def _decision_key(row: Mapping[str, Any]) -> tuple[str, str, str, int, int]:
    decision = row["decision_provenance"]
    return (decision["session_id"], decision["source_runtime_fingerprint"], decision["source_branch_fingerprint"], decision["turn_number"], decision["last_applied_observation_sequence"])


def _next_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("session_id", "state_fingerprint", "last_applied_observation_sequence", "observation_id", "turn_number")}


def _digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _sequence(value: Any, *, zero: bool) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= (0 if zero else 1)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(_plain(value), sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _failure(schema: str, reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": schema, "reason": reason})
