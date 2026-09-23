"""Offline decision-point as-of shell over supplied boundary certificates.

The supplied boundary certificate is a contract input, not a proof that all
decision opportunities were captured.  In particular, execution never creates
a boundary and cannot authenticate a player-selected command.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_strategy_transition_replay import (
    ACTION_IDENTITY_SEMANTICS, SCHEMA_VERSION as TRANSITION_SCHEMA,
)


SCHEMA_VERSION = "offline-decision-point-provenance-v1"
BOUNDARY_SCHEMA = "decision-opportunity-boundary-certificate-v1"
CHANNEL_SOURCE_SCHEMA = "decision-channel-source-v1"
CHANNELS = frozenset({"spectator", "actor_first_person", "simulator_input"})
DECISION_KINDS = frozenset({"team_preview", "turn_start", "forced_replacement", "mid_turn_replacement", "unknown"})
CHOICE_EVIDENCE_STATUSES = frozenset({"direct", "none", "not_applicable"})
_CONTEXT_KEYS = frozenset({"ruleset_id", "mechanics_version", "protocol_version", "battle_format_id"})


def fingerprint_decision_channel_prefix(events: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]]) -> str:
    """Audit digest for a canonical channel prefix, not proof of causality."""
    return hashlib.sha256(_canonical(events)).hexdigest()


def fingerprint_decision_contract_reference(value: Mapping[str, Any]) -> str:
    """Pin context or legal-set input in a boundary certificate."""
    return hashlib.sha256(_canonical(value)).hexdigest()


def materialize_offline_decision_point(
    *,
    boundary_certificate: Mapping[str, Any],
    channel_source: Mapping[str, Any],
    context_reference: Mapping[str, Any],
    legal_action_set: Mapping[str, Any],
    post_boundary_end_sequence: int,
    selected_choice_evidence: Mapping[str, Any] | None = None,
    submitted_command_source: Any | None = None,
    execution_replay: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Separate a certified as-of prefix from later evidence, without inference."""
    if not _boundary(boundary_certificate):
        return _failure("boundary_certificate_invalid")
    boundary = boundary_certificate
    if not _context(context_reference):
        return _failure("context_reference_invalid")
    if not _source_header(channel_source, boundary):
        return _failure("channel_source_or_actor_mismatch")
    if not _legal(legal_action_set):
        return _failure("legal_action_set_invalid")
    if (fingerprint_decision_contract_reference(context_reference) != boundary["context_fingerprint"]
            or fingerprint_decision_contract_reference(legal_action_set) != boundary["legal_action_set_fingerprint"]):
        return _failure("boundary_reference_fingerprint_mismatch")
    cutoff = boundary["after_event_sequence"]
    if not _sequence(post_boundary_end_sequence, zero=True) or post_boundary_end_sequence < cutoff:
        return _failure("post_boundary_window_invalid")
    events = channel_source.get("events")
    if not isinstance(events, (tuple, list)):
        return _failure("channel_events_invalid")
    prefix = []
    seen = set()
    for event in events:
        if not isinstance(event, Mapping) or not _sequence(event.get("sequence")):
            return _failure("channel_event_sequence_invalid")
        if event["sequence"] > cutoff:
            continue
        if event["sequence"] in seen:
            return _failure("channel_event_sequence_invalid")
        seen.add(event["sequence"])
        if (
            event.get("session_id") != boundary["session_id"]
            or event.get("channel") != boundary["channel"]
            or not _sequence(event.get("available_at_sequence"))
            or event["available_at_sequence"] > cutoff
            or not _token(event.get("event_kind"))
            or not isinstance(event.get("payload"), Mapping)
        ):
            return _failure("future_or_foreign_event_in_pre_boundary")
        prefix.append(event)
    prefix.sort(key=lambda item: item["sequence"])
    try:
        prefix_fingerprint = fingerprint_decision_channel_prefix(prefix)
    except (TypeError, ValueError, OverflowError):
        return _failure("channel_prefix_malformed")
    if len(prefix) != boundary["prefix_event_count"] or prefix_fingerprint != boundary["prefix_fingerprint"]:
        return _failure("prefix_fingerprint_mismatch")
    legal_status = legal_action_set["status"]
    choices = tuple(sorted(legal_action_set["action_ids"])) if legal_status != "unknown" else ()
    opportunity = (
        "no_free_choice" if legal_status == "exact" and len(choices) == 1
        else "free" if legal_status == "exact" and len(choices) > 1
        else "unknown"
    )
    choice = {"status": "none"} if selected_choice_evidence is None else selected_choice_evidence
    if not isinstance(choice, Mapping) or choice.get("status") not in CHOICE_EVIDENCE_STATUSES:
        return _failure("selected_choice_evidence_invalid")
    direct_choice = None
    if choice["status"] == "direct":
        if submitted_command_source is None:
            return _failure("direct_choice_producer_unavailable")
        # Import locally: the command owner uses this materializer to validate
        # opportunity records, while the materializer must check its live ledger.
        from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource
        if (not isinstance(submitted_command_source, SessionBoundSubmittedCommandEvidenceSource)
                or not submitted_command_source.authenticates(choice, boundary)):
            return _failure("direct_choice_authentication_invalid")
        direct_choice = {
            "status": "direct", "selected_choice": choice["command_payload"],
            "command_id": choice["command_id"],
            "source_command_id": choice["source_command_id"],
            "command_source_id": choice["command_source_id"],
            "source_provenance": choice["source_provenance"],
        }
    if choice["status"] == "not_applicable":
        return _failure("not_applicable_choice_unproven")
    if choice["status"] != "direct" and set(choice) != {"status"}:
        return _failure("selected_choice_evidence_invalid")
    execution_link = None
    if execution_replay is not None:
        if not _execution_link(execution_replay, boundary, cutoff, post_boundary_end_sequence):
            return _failure("execution_replay_binding_invalid")
        execution_link = {
            "transition_id": execution_replay["transition_id"],
            "action_identity_semantics": ACTION_IDENTITY_SEMANTICS,
            "executed_action": execution_replay["executed_action"],
        }
    context_fingerprint = boundary["context_fingerprint"]
    identity = {
        "session_id": boundary["session_id"], "battle_id": boundary["battle_id"],
        "boundary_id": boundary["boundary_id"], "source_id": boundary["source_id"],
        "prefix_fingerprint": prefix_fingerprint, "context_fingerprint": context_fingerprint,
        "actor": boundary["actor"], "sequence_domain": boundary["sequence_domain"],
        "certified_runtime_fingerprint": boundary.get("certified_runtime_fingerprint"),
    }
    decision_id = "offline-decision:" + hashlib.sha256(_canonical(identity)).hexdigest()
    pre = {
        "schema_version": SCHEMA_VERSION, "decision_id": decision_id,
        "session_id": boundary["session_id"], "battle_id": boundary["battle_id"],
        "simultaneity_group_id": boundary["simultaneity_group_id"],
        "actor": boundary["actor"], "decision_kind": boundary["decision_kind"],
        "turn_number": boundary["turn_number"],
        "channel": boundary["channel"], "actor_completeness": _actor_completeness(boundary["channel"]),
        "context_reference": context_reference, "context_fingerprint": context_fingerprint,
        "boundary": {"boundary_id": boundary["boundary_id"], "source_id": boundary["source_id"], "after_event_sequence": cutoff},
        "sequence_domain": boundary["sequence_domain"],
        "certified_runtime_fingerprint": boundary.get("certified_runtime_fingerprint"),
        "prefix_fingerprint": prefix_fingerprint, "prefix_events": tuple(prefix),
        "legal_action_set": {"status": legal_status, "action_ids": choices},
        "choice_opportunity": opportunity,
        "actor_assistance_exposure": "unknown",
        "opportunity_completeness": "unproven_without_boundary_producer",
    }
    post = {
        "evidence_window": {"start_exclusive_sequence": cutoff, "end_inclusive_sequence": post_boundary_end_sequence},
        "selected_choice_evidence": direct_choice if direct_choice is not None else {"status": choice["status"], "selected_choice": None},
        "execution_replay_link": execution_link,
    }
    return _freeze({"status": "contract_validated", "schema_version": SCHEMA_VERSION,
                    "decision_id": decision_id, "pre_boundary": pre, "post_boundary": post})


def materialize_offline_decision_point_collection(records: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Reject duplicate or conflicting boundary identities before dataset use."""
    if not isinstance(records, (tuple, list)) or not records:
        return _failure("decision_records_invalid")
    if any(not isinstance(item, MappingProxyType) or item.get("status") != "contract_validated" or item.get("schema_version") != SCHEMA_VERSION for item in records):
        return _failure("decision_record_invalid")
    ids = [item["decision_id"] for item in records]
    boundaries = [(item["pre_boundary"]["session_id"], item["pre_boundary"]["boundary"]["boundary_id"],
                   item["pre_boundary"]["actor"]["side"], item["pre_boundary"]["actor"]["slot_index"]) for item in records]
    if len(set(ids)) != len(ids):
        return _failure("duplicate_decision_id")
    if len(set(boundaries)) != len(boundaries):
        return _failure("conflicting_decision_boundary")
    ordered = sorted(records, key=lambda item: item["decision_id"])
    return _freeze({"status": "contract_validated", "schema_version": "offline-decision-point-collection-v1", "records": tuple(ordered)})


def _boundary(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != BOUNDARY_SCHEMA:
        return False
    if any(not _token(value.get(key)) for key in ("source_id", "session_id", "battle_id", "boundary_id", "simultaneity_group_id")):
        return False
    actor = value.get("actor")
    domain = value.get("sequence_domain")
    if domain not in {"channel_event_sequence", "runtime_observation_sequence"}:
        return False
    if domain == "runtime_observation_sequence" and not _digest(value.get("certified_runtime_fingerprint")):
        return False
    if domain == "channel_event_sequence" and value.get("certified_runtime_fingerprint") is not None:
        return False
    return (
        value.get("channel") in CHANNELS and value.get("decision_kind") in DECISION_KINDS
        and _sequence(value.get("turn_number")) and _sequence(value.get("after_event_sequence"), zero=True)
        and _sequence(value.get("prefix_event_count"), zero=True) and _digest(value.get("prefix_fingerprint"))
        and _digest(value.get("context_fingerprint")) and _digest(value.get("legal_action_set_fingerprint"))
        and isinstance(actor, Mapping) and set(actor) == {"session_id", "side", "slot_index", "pokemon_id"}
        and actor.get("session_id") == value["session_id"] and actor.get("side") in {"self", "opponent"}
        and _sequence(actor.get("slot_index"), zero=True) and _token(actor.get("pokemon_id"))
    )


def _source_header(source: Any, boundary: Mapping[str, Any]) -> bool:
    if not isinstance(source, Mapping) or source.get("schema_version") != CHANNEL_SOURCE_SCHEMA:
        return False
    if any(source.get(key) != boundary[key] for key in ("source_id", "session_id", "battle_id", "channel", "sequence_domain")):
        return False
    return source.get("channel_actor") == (None if boundary["channel"] == "spectator" else boundary["actor"])


def _context(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == _CONTEXT_KEYS and all(_token(item) for item in value.values())


def _legal(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != {"status", "action_ids"} or value.get("status") not in {"exact", "partial", "unknown"}:
        return False
    ids = value["action_ids"]
    return (isinstance(ids, (tuple, list)) and all(_token(item) for item in ids)
            and len(ids) == len(set(ids)) and (value["status"] != "exact" or len(ids) > 0)
            and (value["status"] != "unknown" or not ids))


def _execution_link(row: Any, boundary: Mapping[str, Any], cutoff: int, end: int) -> bool:
    if not isinstance(row, MappingProxyType) or row.get("schema_version") != TRANSITION_SCHEMA or row.get("status") != "resolved" or row.get("action_identity_semantics") != ACTION_IDENTITY_SEMANTICS:
        return False
    if boundary["sequence_domain"] != "runtime_observation_sequence":
        return False
    decision, action = row.get("decision_provenance"), row.get("executed_action")
    return (isinstance(decision, Mapping) and isinstance(action, Mapping)
            and decision.get("session_id") == boundary["session_id"]
            and decision.get("decision_owner") == boundary["actor"]
            and decision.get("source_runtime_fingerprint") == boundary["certified_runtime_fingerprint"]
            and decision.get("last_applied_observation_sequence") == cutoff
            and action.get("actor") == boundary["actor"]
            and _sequence(action.get("observation_sequence"))
            and cutoff < action["observation_sequence"] <= end
            and action.get("turn_number") == boundary["turn_number"]
            and _token(row.get("transition_id")))


def _actor_completeness(channel: str) -> str:
    return "not_complete" if channel == "spectator" else "unknown"


def _token(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _sequence(value: Any, *, zero: bool = False) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= (0 if zero else 1)


def _digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


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


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
