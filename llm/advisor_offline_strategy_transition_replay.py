"""Detached offline (state, action, observed next state) replay linkage.

Execution observations and reducer snapshots remain the truth owners.  This
contract records neither a reward nor a strategy preference.
"""
from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_detached_observed_rng_reconciliation import validate_historical_predictive_action_binding
from llm.advisor_lifecycle_confirmation import EXECUTED_MOVE_SOURCE, FAINT_SOURCE, SWITCH_SOURCE, USER_TRUST
from llm.advisor_reducer_state_model import state_fingerprint, validate_battle_state_unknown_markers
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


SCHEMA_VERSION = "offline-strategy-transition-replay-v1"
# A replay action is authenticated execution, never historical player choice.
ACTION_IDENTITY_SEMANTICS = "observed_executed_action"
_FEATURE_SCHEMA = "offline-learned-strategy-state-action-features-v1"


def materialize_offline_strategy_transition(
    *,
    feature_contract: Mapping[str, Any],
    candidate_id: str,
    decision_runtime_snapshot: Mapping[str, Any],
    decision_turn_number: int,
    observation_snapshot: Mapping[str, Any],
    executed_observation_id: str,
    next_runtime_snapshot: Mapping[str, Any],
    next_state_observation_id: str,
    historical_binding: Mapping[str, Any] | None = None,
    predictive_ledger: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Link one decision row to an authenticated action and later reducer state."""
    if not isinstance(feature_contract, Mapping) or feature_contract.get("status") != "resolved" or feature_contract.get("schema_version") != _FEATURE_SCHEMA:
        return _failure("rejected", "feature_contract_invalid")
    provenance = feature_contract.get("provenance")
    rows = feature_contract.get("rows")
    if not isinstance(provenance, Mapping) or not isinstance(rows, (tuple, list)) or not rows:
        return _failure("rejected", "feature_contract_shape_invalid")
    if not isinstance(candidate_id, str) or not candidate_id:
        return _failure("rejected", "candidate_id_invalid")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("candidate_id") == candidate_id]
    if len(matches) != 1 or len({row.get("candidate_id") for row in rows if isinstance(row, Mapping)}) != len(rows):
        return _failure("rejected", "candidate_not_unique_in_features")
    row = matches[0]
    if (
        row.get("schema_version") != _FEATURE_SCHEMA
        or row.get("action_type") not in {"attack", "manual_switch"}
        or row.get("provenance") != {**provenance, "candidate_id": candidate_id}
        or not _turn(decision_turn_number)
    ):
        return _failure("rejected", "decision_feature_binding_invalid")
    decision = _snapshot(decision_runtime_snapshot)
    if decision is None or decision["session_id"] != provenance.get("session_id") or decision["fingerprint"] != provenance.get("source_runtime_fingerprint"):
        return _failure("rejected", "decision_runtime_fingerprint_mismatch")
    owner = provenance.get("decision_owner")
    if not _owner(owner, decision["session_id"]):
        return _failure("rejected", "decision_owner_invalid")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision_runtime_snapshot, decision_owner=owner)
    if d0.get("status") != "resolved" or d0.get("strategy_preview_fingerprint") != provenance.get("source_branch_fingerprint"):
        return _failure("rejected", "decision_branch_fingerprint_mismatch")
    decision_sequence = decision["state"].get("last_applied_observation_sequence")
    if decision_sequence is None:
        decision_sequence = 0
    if not _sequence(decision_sequence, allow_zero=True):
        return _failure("rejected", "decision_sequence_invalid")

    observations = _observations(observation_snapshot, decision["session_id"])
    if observations is None:
        return _failure("rejected", "observation_collection_invalid")
    execution = observations.get(executed_observation_id)
    if execution is None:
        return _failure("incomplete", "authenticated_execution_unavailable")
    if not _confirmed(execution, decision["session_id"]) or execution.get("turn_number") != decision_turn_number:
        return _failure("rejected", "execution_provenance_or_turn_mismatch")
    execution_sequence = execution["observation_sequence"]
    if execution_sequence <= decision_sequence:
        return _failure("rejected", "execution_not_after_decision")
    if row["action_type"] == "attack":
        checked = _attack_execution(execution, candidate_id, provenance, decision_turn_number, historical_binding, predictive_ledger)
    else:
        checked = _switch_execution(execution, candidate_id, owner, historical_binding, predictive_ledger)
    if checked["status"] != "resolved":
        return checked

    next_state = _snapshot(next_runtime_snapshot)
    if next_state is None:
        return _failure("rejected", "next_runtime_snapshot_invalid")
    if next_state["session_id"] != decision["session_id"]:
        return _failure("rejected", "next_state_session_mismatch")
    if next_state["fingerprint"] == decision["fingerprint"]:
        return _failure("rejected", "next_state_not_later")
    next_sequence = next_state["state"].get("last_applied_observation_sequence")
    if not _sequence(next_sequence) or next_sequence <= decision_sequence or next_sequence < execution_sequence:
        return _failure("rejected", "next_state_sequence_not_later")
    anchor = observations.get(next_state_observation_id)
    if anchor is None:
        return _failure("incomplete", "next_state_observation_unavailable")
    if not _confirmed(anchor, decision["session_id"]):
        return _failure("rejected", "next_state_observation_provenance_invalid")
    if (
        anchor.get("reducer_eligibility") != "candidate"
        or anchor["observation_sequence"] != next_sequence
        or anchor["observation_sequence"] < execution_sequence
        or anchor.get("turn_number") < decision_turn_number
    ):
        return _failure("rejected", "next_state_temporal_provenance_invalid")
    receipt = next_state["state"].get("last_commit_provenance")
    if (
        not isinstance(receipt, Mapping)
        or not isinstance(receipt.get("applied_step_ids"), (tuple, list))
        or anchor["observation_id"] not in receipt["applied_step_ids"]
        or not _digest(receipt.get("base_state_fingerprint"))
        or not _digest(receipt.get("replay_batch_fingerprint"))
    ):
        return _failure("rejected", "next_state_reducer_receipt_invalid")
    if row["action_type"] == "manual_switch" and not _next_switch_owner(next_state["state"], owner, checked["incoming"]):
        return _failure("rejected", "observed_switch_not_in_next_state")

    decision_provenance = {
        **provenance, "turn_number": decision_turn_number,
        "last_applied_observation_sequence": decision_sequence,
    }
    action = {
        "candidate_id": candidate_id, "action_type": row["action_type"],
        "execution_identity": checked["execution_identity"],
        "observation_id": execution["observation_id"],
        "observation_sequence": execution_sequence,
        "turn_number": decision_turn_number,
        "actor": owner,
    }
    next_provenance = {
        "session_id": next_state["session_id"],
        "state_fingerprint": next_state["fingerprint"],
        "last_applied_observation_sequence": next_sequence,
        "observation_id": anchor["observation_id"],
        "turn_number": anchor["turn_number"],
    }
    identity = {
        "decision": decision_provenance, "action": action,
        "next_state": next_provenance, "feature_row": _plain(row),
    }
    transition_id = "offline-transition:" + hashlib.sha256(_canonical(identity)).hexdigest()
    return _freeze({
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "transition_id": transition_id, "completeness": "strict_observed_transition",
        "action_identity_semantics": ACTION_IDENTITY_SEMANTICS,
        "decision_provenance": decision_provenance,
        "executed_action": action,
        "decision_feature_row": row,
        "next_state": {
            **next_provenance,
            "observed_summary": _summary(next_state["state"], owner, observations, next_sequence, execution_sequence),
        },
    })


def _attack_execution(execution, candidate_id, provenance, turn, binding, ledger):
    if binding is None or ledger is None:
        return _failure("incomplete", "historical_action_binding_unavailable")
    checked = validate_historical_predictive_action_binding(binding=binding, predictive_ledger=ledger)
    if checked.get("status") != "resolved":
        return _failure("rejected", "historical_action_binding_invalid")
    if (
        checked.get("candidate_id") != candidate_id
        or checked.get("turn_number") != turn
        or checked.get("session_id") != provenance["session_id"]
        or checked.get("source_runtime_fingerprint") != provenance["source_runtime_fingerprint"]
        or checked.get("source_branch_fingerprint") != provenance["source_branch_fingerprint"]
        or checked.get("decision_owner") != provenance["decision_owner"]
        or checked.get("actor") != provenance["decision_owner"]
    ):
        return _failure("rejected", "stale_or_foreign_historical_binding")
    payload = execution.get("payload")
    if (
        execution.get("event_kind") != "executed_move_observed"
        or execution.get("source") != EXECUTED_MOVE_SOURCE
        or execution.get("reducer_eligibility") != "candidate"
        or not isinstance(payload, Mapping)
        or payload.get("source_action_id") != checked["source_action_id"]
        or payload.get("move_id") != checked["move_id"]
        or execution.get("move_id") != checked["move_id"]
        or execution.get("source_action_id") != checked["source_action_id"]
        or _observation_actor(execution) != checked["actor"]
    ):
        return _failure("rejected", "executed_attack_binding_mismatch")
    return {
        "status": "resolved",
        "execution_identity": {"kind": "historical_action_link", "id": checked["source_action_id"]},
    }


def _switch_execution(execution, candidate_id, owner, binding, ledger):
    if binding is not None or ledger is not None:
        return _failure("rejected", "switch_predictive_binding_not_applicable")
    payload = execution.get("payload")
    if (
        execution.get("event_kind") != "pokemon_switch_observed"
        or execution.get("source") != SWITCH_SOURCE
        or execution.get("reducer_eligibility") != "candidate"
        # The forced-switch producer uses the same lifecycle kind and source,
        # but not the manual-switch admission ID.
        or execution.get("observation_id") != f"{owner['session_id']}:pokemon-switch-{execution['observation_sequence']}"
        or _observation_actor(execution) != owner
        or not isinstance(payload, Mapping)
        or set(payload) != {"switch_out_slot_index", "switch_out_pokemon_id", "switch_in_slot_index", "switch_in_pokemon_id"}
        or payload.get("switch_out_slot_index") != owner["slot_index"]
        or payload.get("switch_out_pokemon_id") != owner["pokemon_id"]
        or not _sequence(payload.get("switch_in_slot_index"), allow_zero=True)
        or not isinstance(payload.get("switch_in_pokemon_id"), str)
        or not payload["switch_in_pokemon_id"]
        or candidate_id != f"manual_switch:{payload['switch_in_pokemon_id']}"
        or (payload["switch_out_slot_index"], payload["switch_out_pokemon_id"]) == (payload["switch_in_slot_index"], payload["switch_in_pokemon_id"])
        or any(execution.get(key) != value for key, value in payload.items())
    ):
        return _failure("rejected", "executed_switch_binding_mismatch")
    incoming = {
        "session_id": owner["session_id"], "side": owner["side"],
        "slot_index": payload["switch_in_slot_index"], "pokemon_id": payload["switch_in_pokemon_id"],
    }
    return {
        "status": "resolved",
        "execution_identity": {"kind": "switch_observation", "id": execution["observation_id"]},
        "incoming": incoming,
    }


def _snapshot(snapshot):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "runtime_snapshot_ready":
        return None
    state, session, fingerprint = snapshot.get("state"), snapshot.get("session_id"), snapshot.get("state_fingerprint")
    if (
        not isinstance(state, Mapping) or not isinstance(session, str) or not session
        or state.get("session_id") != session or not validate_battle_state_unknown_markers(dict(state))
        or not isinstance(fingerprint, str) or len(fingerprint) != 64
        or fingerprint != state_fingerprint(dict(state))
    ):
        return None
    return {"state": state, "session_id": session, "fingerprint": fingerprint}


def _observations(snapshot, session):
    if not isinstance(snapshot, Mapping) or snapshot.get("status") != "ready" or snapshot.get("session_id") != session:
        return None
    rows = snapshot.get("ordered_observations")
    if not isinstance(rows, (tuple, list)):
        return None
    indexed, sequences = {}, set()
    for row in rows:
        if (
            not isinstance(row, Mapping) or row.get("session_id") != session
            or not isinstance(row.get("observation_id"), str) or not row["observation_id"]
            or not _sequence(row.get("observation_sequence"))
            or row["observation_id"] in indexed or row["observation_sequence"] in sequences
        ):
            return None
        indexed[row["observation_id"]] = row
        sequences.add(row["observation_sequence"])
    return indexed


def _confirmed(observation, session):
    return (
        isinstance(observation, Mapping)
        and observation.get("session_id") == session
        and observation.get("trust") == USER_TRUST
        and observation.get("observed") is True
        and observation.get("confirmed") is True
        and _turn(observation.get("turn_number"))
        and _sequence(observation.get("observation_sequence"))
    )


def _observation_actor(observation):
    return {
        "session_id": observation.get("session_id"), "side": observation.get("side"),
        "slot_index": observation.get("slot_index"), "pokemon_id": observation.get("pokemon_id"),
    }


def _next_switch_owner(state, owner, incoming):
    side = state.get(f"{owner['side']}_side")
    if not isinstance(side, Mapping) or side.get("active_slot_index") != incoming["slot_index"]:
        return False
    roster = side.get("pokemon")
    member = roster.get(incoming["slot_index"], roster.get(str(incoming["slot_index"]))) if isinstance(roster, Mapping) else None
    return isinstance(member, Mapping) and member.get("pokemon_id") == incoming["pokemon_id"]


def _summary(state, owner, observations, sequence, execution_sequence):
    side = state.get(f"{owner['side']}_side")
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    member = roster.get(owner["slot_index"], roster.get(str(owner["slot_index"]))) if isinstance(roster, Mapping) else None
    active_slot = side.get("active_slot_index") if isinstance(side, Mapping) else None
    active = roster.get(active_slot, roster.get(str(active_slot))) if isinstance(roster, Mapping) and _sequence(active_slot, allow_zero=True) else None
    active_owner = (
        {"session_id": owner["session_id"], "side": owner["side"], "slot_index": active_slot, "pokemon_id": active["pokemon_id"]}
        if isinstance(active, Mapping) and isinstance(active.get("pokemon_id"), str) and active["pokemon_id"]
        else None
    )
    hp = member.get("current_hp") if isinstance(member, Mapping) else None
    fainted = member.get("fainted") if isinstance(member, Mapping) else None
    faint_observed = any(
        row.get("event_kind") == "pokemon_faint_observed"
        and row.get("source") == FAINT_SOURCE
        and row.get("reducer_eligibility") == "candidate"
        and _confirmed(row, owner["session_id"])
        and _observation_actor(row) == owner
        and execution_sequence <= row["observation_sequence"] <= sequence
        for row in observations.values()
    )
    return {
        "decision_side_active_owner": (
            {"availability": "available", "value": active_owner}
            if active_owner is not None else {"availability": "unavailable", "reason": "active_owner_not_established"}
        ),
        "decision_actor_current_hp": (
            {"availability": "available", "value": hp}
            if isinstance(hp, int) and not isinstance(hp, bool) and hp >= 0
            else {"availability": "unavailable", "reason": "exact_hp_not_established"}
        ),
        "decision_actor_fainted": (
            {"availability": "available", "value": True}
            if fainted is True and faint_observed
            else {"availability": "unavailable", "reason": "terminality_not_observed"}
        ),
        "battle_terminal": {"availability": "unavailable", "reason": "battle_terminality_not_observed"},
    }


def _owner(value, session):
    return (
        isinstance(value, Mapping)
        and set(value) == {"session_id", "side", "slot_index", "pokemon_id"}
        and value.get("session_id") == session
        and value.get("side") in {"self", "opponent"}
        and _sequence(value.get("slot_index"), allow_zero=True)
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _turn(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _sequence(value, *, allow_zero=False):
    return isinstance(value, int) and not isinstance(value, bool) and value >= (0 if allow_zero else 1)


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _canonical(value):
    return json.dumps(_plain(value), sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _failure(status, reason):
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
