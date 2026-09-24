"""Durable, pre-split archive of one battle's retained C6 production evidence."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

from llm.advisor_c6_production_decision_capture import ProductionDecisionCapture
from llm.advisor_c6_production_transition_capture import ProductionObservedTransitionCapture
from llm.advisor_offline_decision_point_provenance import _canonical, _freeze, _plain
from llm.advisor_offline_strategy_episode_dataset import materialize_offline_strategy_episode
from llm.advisor_offline_strategy_episode_terminal_binding import materialize_offline_strategy_episode_terminal_binding
from llm.advisor_offline_strategy_episode_population_context import (
    COMPETITION_CONTEXTS, materialize_offline_strategy_episode_population_context,
)
from llm.advisor_offline_strategy_terminal_learning_target import materialize_offline_strategy_terminal_learning_target
from llm.advisor_session_battle_terminal_outcome_evidence import SessionBoundBattleTerminalOutcomeEvidenceSource


SCHEMA_VERSION = "c6-production-battle-export-v1"


def materialize_c6_production_battle_export(
    *, session_id: str, battle_id: str,
    decision_captures: Sequence[ProductionDecisionCapture],
    transition_captures: Sequence[ProductionObservedTransitionCapture],
    terminal_source: SessionBoundBattleTerminalOutcomeEvidenceSource,
    competition_context: str, optional_population_metadata: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Assemble only live retained evidence; no partition or learner is involved."""
    if (not isinstance(session_id, str) or not session_id
            or not isinstance(battle_id, str) or not battle_id
            or not isinstance(terminal_source, SessionBoundBattleTerminalOutcomeEvidenceSource)
            or (terminal_source.session_id, terminal_source.battle_id, terminal_source.source_kind)
            != (session_id, battle_id, "first_person_battle_stream")):
        return _failure("foreign_battle_or_terminal_source")
    if competition_context not in COMPETITION_CONTEXTS:
        return _failure("competition_context_invalid")
    if not isinstance(decision_captures, (tuple, list)) or not isinstance(transition_captures, (tuple, list)):
        return _failure("capture_collection_invalid")
    if optional_population_metadata is not None and not isinstance(optional_population_metadata, Mapping):
        return _failure("population_metadata_invalid")
    if optional_population_metadata is not None and set(optional_population_metadata) & {"collection_mode", "competition_context"}:
        return _failure("population_metadata_conflict")
    if len({id(owner) for owner in decision_captures}) != len(decision_captures):
        return _failure("duplicate_decision_owner")
    if len({id(owner) for owner in transition_captures}) != len(transition_captures):
        return _failure("duplicate_transition_owner")
    decisions = []
    transitions = []
    for owner in decision_captures:
        if not isinstance(owner, ProductionDecisionCapture) or (owner.session_id, owner.battle_id) != (session_id, battle_id):
            return _failure("foreign_decision_owner")
        snapshot = owner.read_capture_snapshot(captured_session_id=session_id, captured_battle_id=battle_id)
        if snapshot.get("status") != "ready":
            return _failure("decision_snapshot_unavailable")
        decisions.append(snapshot)
    for owner in transition_captures:
        if (not isinstance(owner, ProductionObservedTransitionCapture)
                or not any(owner.decision_capture is captured for captured in decision_captures)
                or (owner.session_id, owner.battle_id) != (session_id, battle_id)):
            return _failure("foreign_transition_owner")
        snapshot = owner.read_snapshot(captured_session_id=session_id, captured_battle_id=battle_id)
        if snapshot.get("status") != "ready":
            return _failure("transition_snapshot_unavailable")
        transitions.append(snapshot)
    decisions.sort(key=lambda row: (row["opportunities"]["source_id"], row["opportunities"]["actor"]["pokemon_id"]))
    transitions.sort(key=lambda row: (row["pending_anchors"][0]["actor"]["pokemon_id"] if row["pending_anchors"] else "",
                                      _canonical(row)))
    terminal = terminal_source.read_snapshot(captured_session_id=session_id, captured_battle_id=battle_id)
    if terminal.get("status") != "ready":
        return _failure("terminal_snapshot_unavailable")

    opportunity_ids = []
    command_ids = []
    contexts = []
    for snapshot in decisions:
        opportunity_ids.extend(row["certificate"]["boundary_id"] for row in snapshot["opportunities"]["opportunities"])
        command_ids.extend(row["boundary_id"] for row in snapshot["submitted_commands"]["command_evidence"])
        contexts.extend(row["context_reference"] for row in snapshot["opportunities"]["opportunities"])
    transition_records = [row for snapshot in transitions for row in snapshot["resolved_transition_records"]]
    resolved_ids = [row["boundary_id"] for row in transition_records]
    if (len(set(opportunity_ids)) != len(opportunity_ids) or len(set(command_ids)) != len(command_ids)
            or len(set(resolved_ids)) != len(resolved_ids)
            or not set(command_ids) <= set(opportunity_ids) or not set(resolved_ids) <= set(opportunity_ids)):
        return _failure("capture_boundary_identity_conflict")
    if contexts and any(context != contexts[0] for context in contexts[1:]):
        return _failure("conflicting_battle_rules_context")
    coverage = {
        "opportunity_boundary_ids": tuple(sorted(opportunity_ids)),
        "direct_command_boundary_ids": tuple(sorted(command_ids)),
        "resolved_transition_boundary_ids": tuple(sorted(resolved_ids)),
        "command_without_transition_boundary_ids": tuple(sorted(set(command_ids) - set(resolved_ids))),
        "transition_without_command_boundary_ids": tuple(sorted(set(resolved_ids) - set(command_ids))),
        "opportunity_count": len(opportunity_ids), "direct_command_count": len(command_ids),
        "resolved_transition_count": len(resolved_ids),
    }
    episode = binding = population = target = None
    episode_availability = {"availability": "unavailable", "reason": "no_resolved_observed_transitions"}
    if transition_records:
        episode = materialize_offline_strategy_episode(tuple(row["transition"] for row in transition_records))
        if episode.get("status") not in {"resolved", "incomplete"}:
            return _failure("episode_materialization_rejected")
        episode_availability = {"availability": "available", "status": episode["status"]}
        binding = materialize_offline_strategy_episode_terminal_binding(episode=episode, terminal_source=terminal_source)
        if binding.get("status") not in {"resolved", "incomplete"}:
            return _failure("terminal_binding_rejected")
        if not contexts:
            return _failure("battle_rules_context_unavailable")
        sampling = {"collection_mode": "first_person_capture", "competition_context": competition_context,
                    **dict(optional_population_metadata or {})}
        population = materialize_offline_strategy_episode_population_context(
            terminal_binding=binding, terminal_source=terminal_source, session_id=session_id,
            battle_id=battle_id, rules_context=contexts[0], sampling_context=sampling)
        if population.get("status") not in {"resolved", "incomplete"}:
            return _failure("population_context_rejected")
        target = materialize_offline_strategy_terminal_learning_target(
            population_context=population, terminal_source=terminal_source)
        if target.get("status") != "materialized":
            return _failure("terminal_target_rejected")
    content = {
        "status": "materialized", "schema_version": SCHEMA_VERSION,
        "session_id": session_id, "battle_id": battle_id,
        "decision_capture_snapshots": tuple(decisions), "transition_capture_snapshots": tuple(transitions),
        "terminal_evidence_snapshot": terminal, "episode_availability": episode_availability,
        "offline_episode": episode, "terminal_binding": binding, "population_context": population,
        "terminal_learning_target": target, "coverage": coverage,
        "limitations": ("pre_split_production_evidence_archive", "external_event_truthfulness_not_independently_verified",
                        "live_source_owners_not_rehydrated_from_json",
                        "no_automatic_training_or_model_promotion"),
    }
    return _freeze({**content, "export_id": "c6-production-export:" + hashlib.sha256(_canonical(content)).hexdigest()})


def write_c6_production_battle_export(*, export_bundle: Mapping[str, Any], output_path: str | Path) -> Mapping[str, Any]:
    """Write once through a sibling temp file, then validate the durable bytes."""
    if (not isinstance(export_bundle, MappingProxyType)
            or export_bundle.get("schema_version") != SCHEMA_VERSION
            or export_bundle.get("status") != "materialized"):
        return _failure("export_bundle_invalid")
    content = {key: value for key, value in export_bundle.items() if key != "export_id"}
    expected_id = "c6-production-export:" + hashlib.sha256(_canonical(content)).hexdigest()
    if export_bundle.get("export_id") != expected_id:
        return _failure("export_identity_invalid")
    try:
        path = Path(output_path)
        if not path.is_absolute() or not path.parent.is_dir():
            return _failure("output_parent_unavailable")
        payload = json.dumps(_plain(export_bundle), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        if path.exists():
            return (_freeze({"status": "written", "schema_version": SCHEMA_VERSION, "export_id": expected_id,
                             "output_path": str(path), "byte_count": len(payload), "content_sha256": digest,
                             "write_disposition": "identical_existing"})
                    if path.is_file() and path.read_bytes() == payload else _failure("destination_content_conflict"))
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".c6-export-",
                                             suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic exclusive link: an intervening writer cannot be overwritten.
            os.link(temporary, path)
            actual = path.read_bytes()
            if actual != payload or json.loads(actual)["export_id"] != expected_id:
                return _failure("written_content_validation_failed")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return _freeze({"status": "written", "schema_version": SCHEMA_VERSION, "export_id": expected_id,
                        "output_path": str(path), "byte_count": len(payload), "content_sha256": digest,
                        "write_disposition": "created"})
    except (OSError, TypeError, ValueError, KeyError):
        return _failure("export_write_failed")


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
