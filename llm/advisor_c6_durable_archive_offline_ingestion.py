"""Strict detached ingestion of one persisted C6 production battle archive.

The archive digest identifies content, not an externally signed event. This
module validates the retained ledgers; it never recreates live source owners.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from llm.advisor_c6_production_battle_export import SCHEMA_VERSION as EXPORT_SCHEMA
from llm.advisor_c6_production_decision_capture import SCHEMA_VERSION as CAPTURE_SCHEMA
from llm.advisor_c6_production_transition_capture import SCHEMA_VERSION as TRANSITION_CAPTURE_SCHEMA
from llm.advisor_offline_decision_point_provenance import (
    _canonical, _freeze, _plain, materialize_offline_decision_point,
)
from llm.advisor_offline_strategy_episode_dataset import materialize_offline_strategy_episode, _transition_surface
from llm.advisor_offline_strategy_episode_population_context import validates_materialized_population_context
from llm.advisor_offline_strategy_terminal_learning_target import validates_materialized_terminal_learning_target
from llm.advisor_session_actor_private_decision_information import (
    PRIVATE_SURFACE_VERSION, SCHEMA_VERSION as PRIVATE_SCHEMA, _completeness,
    _normalize_snapshot as _normalize_private,
)
from llm.advisor_session_decision_public_battle_information import (
    PUBLIC_SURFACE_VERSION, SCHEMA_VERSION as PUBLIC_SCHEMA,
    _normalize_snapshot as _normalize_public,
)
from llm.advisor_session_decision_opportunity_source import SOURCE_SCHEMA as OPPORTUNITY_SCHEMA
from llm.advisor_session_submitted_command_evidence_source import (
    SCHEMA_VERSION as COMMAND_SCHEMA, _command,
)
from llm.advisor_session_battle_terminal_outcome_evidence import (
    SCHEMA_VERSION as TERMINAL_SCHEMA, TERMINATION_CAUSES,
)


SCHEMA_VERSION = "c6-durable-archive-offline-ingestion-v1"
LIMITATIONS = ("archive_content_identity_is_not_external_event_signature",
               "historical_detached_evidence_not_live_source_authority",
               "evaluation_partition_requires_external_manifest")
_EXPORT_KEYS = {"status", "schema_version", "session_id", "battle_id", "decision_capture_snapshots",
                "transition_capture_snapshots", "terminal_evidence_snapshot", "episode_availability",
                "offline_episode", "terminal_binding", "population_context", "terminal_learning_target",
                "coverage", "limitations", "export_id"}
_PUBLIC_KEYS = {"status", "schema_version", "public_information_id", "public_surface_version",
                "public_snapshot_fingerprint", "source_provenance", "source_public_event_id",
                "session_id", "battle_id", "opportunity_source_id", "bound_command_source_id",
                "public_source_id", "channel", "actor", "boundary_id", "decision_kind",
                "turn_number", "prefix_fingerprint", "context_fingerprint", "scope_limitation",
                "directness_limitation", "public_snapshot"}
_PRIVATE_KEYS = {"status", "schema_version", "private_information_id", "private_surface_version",
                 "source_provenance", "source_private_event_id", "session_id", "battle_id",
                 "opportunity_source_id", "bound_command_source_id", "private_source_id",
                 "channel", "actor", "boundary_id", "decision_kind", "turn_number",
                 "prefix_fingerprint", "context_fingerprint", "private_snapshot_fingerprint",
                 "completeness", "private_snapshot"}
_COMMAND_KEYS = {"status", "schema_version", "command_id", "source_command_id",
                 "source_provenance", "session_id", "battle_id", "opportunity_source_id",
                 "command_source_id", "channel", "actor", "boundary_id", "decision_kind",
                 "turn_number", "prefix_fingerprint", "context_fingerprint",
                 "legal_action_set_fingerprint", "command_payload"}
_CAPTURE_KEYS = {"status", "schema_version", "session_id", "battle_id", "opportunities",
                 "public_information", "private_information", "submitted_commands", "scope"}
_OPPORTUNITY_KEYS = {"status", "schema_version", "session_id", "battle_id", "source_id",
                     "channel", "actor", "sequence_domain", "opportunity_scope",
                     "channel_source", "opportunities"}
_PUBLIC_SOURCE_KEYS = {"status", "schema_version", "session_id", "battle_id",
                       "opportunity_source_id", "bound_command_source_id", "public_source_id",
                       "channel", "actor", "public_surface_version", "scope_limitation",
                       "directness_limitation", "evidence"}
_PRIVATE_SOURCE_KEYS = {"status", "schema_version", "session_id", "battle_id",
                        "opportunity_source_id", "bound_command_source_id", "private_source_id",
                        "channel", "actor", "private_surface_version", "completeness_scope", "evidence"}
_COMMAND_SOURCE_KEYS = {"status", "schema_version", "session_id", "battle_id",
                        "opportunity_source_id", "command_source_id", "channel", "actor",
                        "command_evidence", "command_unknown_boundary_ids"}
_TRANSITION_CAPTURE_KEYS = {"status", "schema_version", "session_id", "battle_id",
                            "pending_anchors", "resolved_transitions", "resolved_transition_records",
                            "latest_attempts"}
_TERMINAL_SOURCE_KEYS = {"status", "schema_version", "session_id", "battle_id", "source_id",
                         "source_kind", "terminal_evidence", "stream_end_evidence", "outcome_evidence",
                         "terminality_availability"}


def load_c6_production_battle_export(*, input_path: str | Path) -> Mapping[str, Any]:
    """Read JSON and validate every source ledger before offline use."""
    try:
        def unique_pairs(pairs):
            if len({key for key, _ in pairs}) != len(pairs):
                raise ValueError("duplicate_json_key")
            return dict(pairs)
        raw = json.loads(Path(input_path).read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))
    except (OSError, UnicodeError, ValueError, TypeError):
        return _failure("archive_json_invalid")
    return ingest_c6_production_battle_export(raw)


def ingest_c6_production_battle_export(raw: Any) -> Mapping[str, Any]:
    """Validate a parsed archive without treating plain mappings as authority."""
    try:
        if (not isinstance(raw, Mapping) or set(raw) != _EXPORT_KEYS
                or raw["status"] != "materialized" or raw["schema_version"] != EXPORT_SCHEMA):
            return _failure("archive_schema_invalid")
        archive = _freeze(raw)
        content = {key: value for key, value in archive.items() if key != "export_id"}
        expected = "c6-production-export:" + hashlib.sha256(_canonical(content)).hexdigest()
        if archive["export_id"] != expected:
            return _failure("archive_content_identity_mismatch")
        session, battle = archive["session_id"], archive["battle_id"]
        if not all(isinstance(value, str) and value for value in (session, battle)):
            return _failure("archive_battle_identity_invalid")
        if (archive["limitations"] != ("pre_split_production_evidence_archive",
                "external_event_truthfulness_not_independently_verified",
                "live_source_owners_not_rehydrated_from_json",
                "no_automatic_training_or_model_promotion")
                or not isinstance(archive["decision_capture_snapshots"], tuple)
                or not isinstance(archive["transition_capture_snapshots"], tuple)):
            return _failure("archive_structure_invalid")
        boundaries = []
        source_ids = set()
        for capture in archive["decision_capture_snapshots"]:
            admitted = _decision_capture(capture, session, battle)
            if admitted is None:
                return _failure("decision_capture_invalid")
            source_id = capture["opportunities"]["source_id"]
            if source_id in source_ids:
                return _failure("duplicate_decision_source")
            source_ids.add(source_id)
            boundaries.extend(admitted)
        ids = [row["boundary_id"] for row in boundaries]
        if len(ids) != len(set(ids)):
            return _failure("duplicate_boundary")
        by_boundary = {row["boundary_id"]: row for row in boundaries}
        transitions = []
        resolved_ids = []
        for capture in archive["transition_capture_snapshots"]:
            checked = _transition_capture(capture, session, battle, by_boundary)
            if checked is None:
                return _failure("transition_capture_invalid")
            transitions.extend(row["transition"] for row in checked)
            resolved_ids.extend(row["boundary_id"] for row in checked)
        if len(resolved_ids) != len(set(resolved_ids)):
            return _failure("duplicate_resolved_boundary")
        commands = [row["boundary_id"] for row in boundaries if row["submitted_command"] is not None]
        coverage = {
            "opportunity_boundary_ids": tuple(sorted(ids)),
            "direct_command_boundary_ids": tuple(sorted(commands)),
            "resolved_transition_boundary_ids": tuple(sorted(resolved_ids)),
            "command_without_transition_boundary_ids": tuple(sorted(set(commands) - set(resolved_ids))),
            "transition_without_command_boundary_ids": tuple(sorted(set(resolved_ids) - set(commands))),
            "opportunity_count": len(ids), "direct_command_count": len(commands),
            "resolved_transition_count": len(resolved_ids),
        }
        if archive["coverage"] != coverage:
            return _failure("coverage_cross_link_invalid")
        contexts = [row["opportunity_record"]["context_reference"] for row in boundaries]
        if contexts and any(context != contexts[0] for context in contexts[1:]):
            return _failure("conflicting_battle_context")
        if not _terminal_and_offline(archive, session, battle, tuple(transitions), contexts):
            return _failure("terminal_or_offline_artifact_invalid")
        ordered = tuple(sorted(boundaries, key=lambda row: row["boundary_id"]))
        identity = {"export_id": archive["export_id"], "boundary_ids": tuple(sorted(ids)),
                    "target_record_id": archive["terminal_learning_target"]["target_record_id"]
                    if archive["terminal_learning_target"] is not None else None}
        return _freeze({"status": "validated", "schema_version": SCHEMA_VERSION,
                        "ingestion_id": "c6-detached-ingestion:" + hashlib.sha256(_canonical(identity)).hexdigest(),
                        "export_id": archive["export_id"], "session_id": session, "battle_id": battle,
                        "terminal_target": archive["terminal_learning_target"], "boundaries": ordered,
                        "coverage": coverage, "archive": archive, "limitations": LIMITATIONS})
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, AttributeError):
        return _failure("archive_nested_evidence_invalid")


def validates_c6_ingested_archive(value: Any) -> bool:
    if not isinstance(value, MappingProxyType) or value.get("schema_version") != SCHEMA_VERSION:
        return False
    checked = ingest_c6_production_battle_export(_plain(value.get("archive")))
    return checked.get("status") == "validated" and checked == value


def _decision_capture(capture: Mapping[str, Any], session: str, battle: str) -> tuple[Mapping[str, Any], ...] | None:
    if (not isinstance(capture, Mapping) or set(capture) != _CAPTURE_KEYS
            or capture.get("scope") != "in_memory_admitted_decisions_only"
            or capture.get("schema_version") != CAPTURE_SCHEMA
            or capture.get("status") != "ready" or capture.get("session_id") != session
            or capture.get("battle_id") != battle):
        return None
    opportunity = capture["opportunities"]
    public, private, commands = (capture[key] for key in ("public_information", "private_information", "submitted_commands"))
    actor = opportunity["actor"]
    source_id = opportunity["source_id"]
    command_id = source_id + ":command"
    if (set(opportunity) != _OPPORTUNITY_KEYS or set(public) != _PUBLIC_SOURCE_KEYS
            or set(private) != _PRIVATE_SOURCE_KEYS or set(commands) != _COMMAND_SOURCE_KEYS
            or opportunity["status"] != "ready" or opportunity["schema_version"] != OPPORTUNITY_SCHEMA
            or opportunity["session_id"] != session or opportunity["battle_id"] != battle
            or opportunity["channel"] != "actor_first_person" or actor["side"] != "self"
            or opportunity["sequence_domain"] != "channel_event_sequence"
            or opportunity["opportunity_scope"] != "admitted_to_this_source_only"):
        return None
    channel_source = opportunity["channel_source"]
    if (channel_source["source_id"] != source_id or channel_source["session_id"] != session
            or channel_source["battle_id"] != battle or channel_source["channel"] != "actor_first_person"
            or channel_source["channel_actor"] != actor
            or channel_source["sequence_domain"] != "channel_event_sequence"
            or not isinstance(channel_source["events"], tuple)):
        return None
    for sequence, event in enumerate(channel_source["events"], start=1):
        if (event["sequence"] != sequence or event["available_at_sequence"] != sequence
                or event["session_id"] != session or event["channel"] != "actor_first_person"
                or event["event_kind"] != "channel_evidence_marker"):
            return None
    for snapshot, schema, own_id in ((public, PUBLIC_SCHEMA, "public_source_id"),
                                     (private, PRIVATE_SCHEMA, "private_source_id"),
                                     (commands, COMMAND_SCHEMA, "command_source_id")):
        if (snapshot["status"] != "ready" or snapshot["schema_version"] != schema
                or snapshot["session_id"] != session or snapshot["battle_id"] != battle
                or snapshot["opportunity_source_id"] != source_id or snapshot["actor"] != actor
                or snapshot["channel"] != "actor_first_person"
                or snapshot[own_id] != source_id + (":command" if own_id == "command_source_id"
                                                   else ":public" if own_id == "public_source_id" else ":private")):
            return None
    if (public["bound_command_source_id"] != command_id or private["bound_command_source_id"] != command_id
            or public["public_surface_version"] != PUBLIC_SURFACE_VERSION
            or public["scope_limitation"] != "v1_supported_public_surface_only"
            or public["directness_limitation"] != "external_actor_visibility_not_independently_verified"
            or private["private_surface_version"] != PRIVATE_SURFACE_VERSION
            or private["completeness_scope"] != "v1_supported_own_side_surface_only"):
        return None
    opportunities = opportunity["opportunities"]
    if not isinstance(opportunities, tuple):
        return None
    public_by = _indexed(public["evidence"])
    private_by = _indexed(private["evidence"])
    command_by = _indexed(commands["command_evidence"])
    if any(index is None for index in (public_by, private_by, command_by)):
        return None
    boundary_ids = [row["certificate"]["boundary_id"] for row in opportunities]
    if (len(boundary_ids) != len(set(boundary_ids)) or set(public_by) != set(boundary_ids)
            or set(private_by) != set(boundary_ids) or not set(command_by) <= set(boundary_ids)
            or commands["command_unknown_boundary_ids"] != tuple(sorted(set(boundary_ids) - set(command_by)))):
        return None
    if (opportunities != tuple(sorted(opportunities, key=lambda row: row["certificate"]["boundary_id"]))
            or public["evidence"] != tuple(public_by[key] for key in sorted(public_by))
            or private["evidence"] != tuple(private_by[key] for key in sorted(private_by))
            or commands["command_evidence"] != tuple(command_by[key] for key in sorted(command_by))):
        return None
    result = []
    for retained in opportunities:
        if set(retained) != {"certificate", "channel_source", "context_reference", "legal_action_set"}:
            return None
        boundary = retained["certificate"]
        boundary_id = boundary["boundary_id"]
        pub, priv, command = public_by[boundary_id], private_by[boundary_id], command_by.get(boundary_id)
        if (boundary["session_id"] != session or boundary["battle_id"] != battle
                or boundary["source_id"] != source_id or boundary["actor"] != actor
                or boundary["channel"] != "actor_first_person"
                or retained["channel_source"]["events"] != opportunity["channel_source"]["events"][:boundary["prefix_event_count"]]):
            return None
        decision = materialize_offline_decision_point(
            boundary_certificate=boundary, channel_source=retained["channel_source"],
            context_reference=retained["context_reference"], legal_action_set=retained["legal_action_set"],
            post_boundary_end_sequence=boundary["after_event_sequence"])
        if decision.get("status") != "contract_validated":
            return None
        if not _public_record(pub, boundary, source_id, command_id):
            return None
        if not _private_record(priv, boundary, source_id, command_id):
            return None
        opportunity_id = pub["source_public_event_id"].removesuffix(":public")
        expected_boundary = "decision-boundary:" + hashlib.sha256(
            f"{session}\x1f{battle}\x1f{source_id}\x1f{opportunity_id}".encode("utf-8")).hexdigest()
        if (pub["source_public_event_id"] != opportunity_id + ":public"
                or priv["source_private_event_id"] != opportunity_id + ":private"
                or boundary_id != expected_boundary):
            return None
        production_id = (f"turn:{boundary['turn_number']}:kind:{boundary['decision_kind']}:runtime:")
        if not opportunity_id.startswith(production_id):
            return None
        if command is not None and not _command_record(command, boundary, source_id, command_id):
            return None
        result.append(_freeze({
            "boundary_id": boundary_id,
            "opportunity_record": {"status": "captured", "schema_version": OPPORTUNITY_SCHEMA, **retained},
            "public_information": pub, "private_information": priv,
            "submitted_command": command,
            "choice_availability": {"availability": "available"} if command is not None else
                                   {"availability": "unavailable", "reason": "direct_command_not_observed"},
            "decision_point_without_choice": decision,
            "source_ids": {"opportunity": source_id, "command": command_id,
                           "public": public["public_source_id"], "private": private["private_source_id"]},
        }))
    return tuple(result)


def _indexed(rows: Any) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(rows, tuple):
        return None
    result = {}
    for row in rows:
        if (not isinstance(row, Mapping) or not isinstance(row.get("boundary_id"), str)
                or row["boundary_id"] in result):
            return None
        result[row["boundary_id"]] = row
    return result


def _public_record(row: Mapping[str, Any], boundary: Mapping[str, Any], source: str, command_source: str) -> bool:
    if set(row) != _PUBLIC_KEYS:
        return False
    snapshot = row["public_snapshot"]
    normalized = _normalize_public(snapshot, boundary["actor"])
    fingerprint = hashlib.sha256(_canonical(snapshot)).hexdigest()
    identity = {"session_id": boundary["session_id"], "battle_id": boundary["battle_id"],
                "boundary_id": boundary["boundary_id"], "actor": boundary["actor"],
                "source_id": source + ":public", "source_public_event_id": row["source_public_event_id"],
                "public_surface_version": PUBLIC_SURFACE_VERSION, "public_snapshot_fingerprint": fingerprint}
    return (row["status"] == "direct_pre_command" and row["schema_version"] == PUBLIC_SCHEMA
            and normalized == snapshot and row["public_snapshot_fingerprint"] == fingerprint
            and row["public_information_id"] == "decision-public-information:" + hashlib.sha256(_canonical(identity)).hexdigest()
            and row["public_surface_version"] == PUBLIC_SURFACE_VERSION
            and row["source_provenance"] == "direct_pre_command_public_admission"
            and row["scope_limitation"] == "v1_supported_public_surface_only"
            and row["directness_limitation"] == "external_actor_visibility_not_independently_verified"
            and row["opportunity_source_id"] == source and row["bound_command_source_id"] == command_source
            and row["public_source_id"] == source + ":public"
            and all(row[key] == boundary[key] for key in (
                "session_id", "battle_id", "channel", "actor", "boundary_id", "decision_kind",
                "turn_number", "prefix_fingerprint", "context_fingerprint")))


def _private_record(row: Mapping[str, Any], boundary: Mapping[str, Any], source: str, command_source: str) -> bool:
    if set(row) != _PRIVATE_KEYS:
        return False
    snapshot = row["private_snapshot"]
    raw = _plain(snapshot)
    for own in raw["own_roster"]:
        for move in own["moves"]:
            for key in ("move_id", "current_pp"):
                wrapped = move[key]
                move[key] = wrapped.get("value") if wrapped["availability"] == "available" else None
    normalized = _normalize_private(raw, boundary["actor"])
    fingerprint = hashlib.sha256(_canonical(snapshot)).hexdigest()
    identity = {"session_id": boundary["session_id"], "battle_id": boundary["battle_id"],
                "actor": boundary["actor"], "boundary_id": boundary["boundary_id"],
                "opportunity_source_id": source, "private_source_id": source + ":private",
                "source_private_event_id": row["source_private_event_id"],
                "private_snapshot_fingerprint": fingerprint,
                "private_surface_version": PRIVATE_SURFACE_VERSION}
    return (row["status"] == "direct_pre_command" and row["schema_version"] == PRIVATE_SCHEMA
            and normalized == snapshot and row["private_snapshot_fingerprint"] == fingerprint
            and row["completeness"] == _completeness(snapshot)
            and row["private_information_id"] == "actor-private-information:" + hashlib.sha256(_canonical(identity)).hexdigest()
            and row["private_surface_version"] == PRIVATE_SURFACE_VERSION
            and row["source_provenance"] == "direct_pre_command_actor_private_admission"
            and row["opportunity_source_id"] == source and row["bound_command_source_id"] == command_source
            and row["private_source_id"] == source + ":private"
            and all(row[key] == boundary[key] for key in (
                "session_id", "battle_id", "channel", "actor", "boundary_id", "decision_kind",
                "turn_number", "prefix_fingerprint", "context_fingerprint")))


def _command_record(row: Mapping[str, Any], boundary: Mapping[str, Any], source: str, command_source: str) -> bool:
    if set(row) != _COMMAND_KEYS:
        return False
    identity = {"session_id": boundary["session_id"], "battle_id": boundary["battle_id"],
                "opportunity_source_id": source, "command_source_id": command_source,
                "channel": boundary["channel"], "actor": boundary["actor"],
                "boundary_id": boundary["boundary_id"], "source_command_id": row["source_command_id"],
                "command_payload": row["command_payload"]}
    return (row["status"] == "direct" and row["schema_version"] == COMMAND_SCHEMA
            and row["source_provenance"] == "direct_command_input_admission"
            and _command(row["command_payload"], boundary["decision_kind"])
            and row["command_id"] == "submitted-command:" + hashlib.sha256(_canonical(identity)).hexdigest()
            and row["opportunity_source_id"] == source and row["command_source_id"] == command_source
            and all(row[key] == boundary[key] for key in (
                "session_id", "battle_id", "channel", "actor", "boundary_id", "decision_kind",
                "turn_number", "prefix_fingerprint", "context_fingerprint", "legal_action_set_fingerprint")))


def _transition_capture(capture: Mapping[str, Any], session: str, battle: str,
                        boundaries: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...] | None:
    if (set(capture) != _TRANSITION_CAPTURE_KEYS
            or capture["status"] != "ready" or capture["schema_version"] != TRANSITION_CAPTURE_SCHEMA
            or capture["session_id"] != session or capture["battle_id"] != battle):
        return None
    records = capture["resolved_transition_records"]
    if (not isinstance(records, tuple) or capture["resolved_transitions"] != tuple(row["transition"] for row in records)
            or len({row["boundary_id"] for row in records}) != len(records)):
        return None
    for row in records:
        boundary_id = row["boundary_id"]
        if boundary_id not in boundaries or not _transition_surface(row["transition"]):
            return None
        owner = boundaries[boundary_id]["opportunity_record"]["certificate"]["actor"]
        boundary = boundaries[boundary_id]["opportunity_record"]["certificate"]
        opportunity_id = boundaries[boundary_id]["public_information"]["source_public_event_id"].removesuffix(":public")
        runtime_fingerprint = opportunity_id.rsplit(":runtime:", 1)[-1]
        if (row["transition"]["decision_provenance"]["decision_owner"] != owner
                or row["transition"]["decision_provenance"]["session_id"] != session
                or row["transition"]["decision_provenance"]["turn_number"] != boundary["turn_number"]
                or row["transition"]["decision_provenance"]["source_runtime_fingerprint"] != runtime_fingerprint):
            return None
    for anchor in capture["pending_anchors"]:
        boundary_id = anchor["boundary_id"]
        if boundary_id not in boundaries:
            return None
        boundary = boundaries[boundary_id]["opportunity_record"]["certificate"]
        if (anchor["session_id"] != session or anchor["battle_id"] != battle
                or anchor["actor"] != boundary["actor"]
                or anchor["decision_turn_number"] != boundary["turn_number"]
                or anchor["decision_runtime_snapshot"]["session_id"] != session):
            return None
    if any(row["boundary_id"] not in boundaries for row in capture["latest_attempts"]):
        return None
    return records


def _terminal_and_offline(archive: Mapping[str, Any], session: str, battle: str,
                          transitions: tuple[Mapping[str, Any], ...], contexts: list[Mapping[str, Any]]) -> bool:
    terminal = archive["terminal_evidence_snapshot"]
    if (set(terminal) != _TERMINAL_SOURCE_KEYS
            or terminal["status"] != "ready" or terminal["schema_version"] != TERMINAL_SCHEMA
            or terminal["session_id"] != session or terminal["battle_id"] != battle
            or terminal["source_kind"] != "first_person_battle_stream"):
        return False
    evidence = terminal["outcome_evidence"]
    if evidence is not None:
        direct = evidence["authority"] == "direct_final_declaration"
        expected_keys = ({"schema_version", "evidence_id", "session_id", "battle_id", "source_id",
                          "source_kind", "authority", "source_event_sequence", "turn_number",
                          "declared_result", "termination_cause", "evidence_completeness", "battle_terminal"}
                         | ({"source_terminal_event_id", "raw_termination_cause", "source_cause_event_id"}
                            if direct else {"source_stream_end_event_id"}))
        if (evidence["schema_version"] != TERMINAL_SCHEMA or evidence["session_id"] != session
                or set(evidence) != expected_keys
                or evidence["battle_id"] != battle or evidence["source_id"] != terminal["source_id"]
                or evidence["source_kind"] != terminal["source_kind"]
                or evidence["battle_terminal"] is not direct
                or (direct and (evidence["declared_result"] not in {"self", "opponent", "tie"}
                                or evidence["termination_cause"] not in TERMINATION_CAUSES
                                or evidence["evidence_completeness"] != "final_declaration_observed"))
                or (not direct and (evidence["authority"] != "direct_stream_end_marker"
                                    or evidence["declared_result"] != "none_observed"
                                    or evidence["evidence_completeness"] != "stream_ended_without_declaration"))):
            return False
        facts = {key: value for key, value in evidence.items() if key not in {"schema_version", "evidence_id"}}
        expected = ("battle-terminal:" if direct else "stream-end:") + hashlib.sha256(_canonical(facts)).hexdigest()
        if evidence["evidence_id"] != expected:
            return False
    if (terminal["terminal_evidence"] != (evidence if evidence is not None and evidence["battle_terminal"] else None)
            or terminal["stream_end_evidence"] != (evidence if evidence is not None and not evidence["battle_terminal"] else None)
            or terminal["terminality_availability"] != ("observed" if evidence is not None and evidence["battle_terminal"] else "unavailable")):
        return False
    if not transitions:
        return (archive["offline_episode"] is None and archive["terminal_binding"] is None
                and archive["population_context"] is None and archive["terminal_learning_target"] is None
                and archive["episode_availability"] == {"availability": "unavailable", "reason": "no_resolved_observed_transitions"})
    if not contexts:
        return False
    episode = materialize_offline_strategy_episode(transitions)
    population = archive["population_context"]
    target = archive["terminal_learning_target"]
    binding = archive["terminal_binding"]
    return (episode.get("status") in {"resolved", "incomplete"} and archive["offline_episode"] == episode
            and archive["episode_availability"] == {"availability": "available", "status": episode["status"]}
            and isinstance(binding, Mapping) and binding["base_episode"] == episode
            and binding["session_id"] == session and binding["battle_id"] == battle
            and binding["terminal_outcome"]["evidence"] == evidence
            and binding["terminal_source"] == {"source_id": terminal["source_id"], "source_kind": terminal["source_kind"]}
            and isinstance(population, MappingProxyType) and validates_materialized_population_context(population)
            and population["base_terminal_binding"] == binding
            and population["rules_context"] == contexts[0]
            and population["sampling_context"]["collection_mode"] == "first_person_capture"
            and isinstance(target, MappingProxyType) and validates_materialized_terminal_learning_target(target)
            and target["base_population_context"] == population)


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
