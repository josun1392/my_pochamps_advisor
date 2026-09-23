"""Auditable observational choices paired with battle-level terminal targets."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import (
    _freeze,
    fingerprint_decision_contract_reference,
    materialize_offline_decision_point,
)
from llm.advisor_offline_strategy_evaluation_split import (
    PARTITIONS,
    validates_materialized_evaluation_split,
)
from llm.advisor_offline_strategy_terminal_learning_target import (
    materialize_offline_strategy_terminal_learning_target,
)
from llm.advisor_session_actor_private_decision_information import (
    PRIVATE_SURFACE_VERSION,
    SessionBoundActorPrivateDecisionInformationSource,
)
from llm.advisor_session_battle_terminal_outcome_evidence import SessionBoundBattleTerminalOutcomeEvidenceSource
from llm.advisor_session_decision_opportunity_source import SessionBoundDecisionOpportunityBoundarySource
from llm.advisor_session_decision_opportunity_source import SOURCE_SCHEMA as OPPORTUNITY_SOURCE_SCHEMA
from llm.advisor_session_submitted_command_evidence_source import SessionBoundSubmittedCommandEvidenceSource


SCHEMA_VERSION = "offline-strategy-choice-outcome-example-v1"
LIMITATIONS = (
    "decision_to_episode_transition_membership_not_proven",
    "observational_terminal_outcome_not_causal_action_value",
    "battle_join_session_and_battle_only",
)


def materialize_offline_strategy_choice_outcome_example(
    *, opportunity_record: Mapping[str, Any],
    opportunity_source: SessionBoundDecisionOpportunityBoundarySource,
    private_information: Mapping[str, Any],
    private_source: SessionBoundActorPrivateDecisionInformationSource,
    submitted_command: Mapping[str, Any],
    command_source: SessionBoundSubmittedCommandEvidenceSource,
    terminal_target: Mapping[str, Any],
    terminal_source: SessionBoundBattleTerminalOutcomeEvidenceSource,
    evaluation_split: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Join only exact live evidence and an externally fixed evaluation partition."""
    if (not isinstance(opportunity_source, SessionBoundDecisionOpportunityBoundarySource)
            or not isinstance(private_source, SessionBoundActorPrivateDecisionInformationSource)
            or not isinstance(command_source, SessionBoundSubmittedCommandEvidenceSource)
            or not isinstance(terminal_source, SessionBoundBattleTerminalOutcomeEvidenceSource)):
        return _failure("source_invalid")
    if (private_source.opportunity_source is not opportunity_source
            or private_source.command_source is not command_source
            or command_source.opportunity_source is not opportunity_source):
        return _failure("source_owner_mismatch")
    if not isinstance(opportunity_record, MappingProxyType):
        return _failure("opportunity_not_retained")
    if (set(opportunity_record) != {
        "status", "schema_version", "certificate", "channel_source",
        "context_reference", "legal_action_set",
    } or opportunity_record.get("status") not in {"captured", "duplicate"}
            or opportunity_record.get("schema_version") != OPPORTUNITY_SOURCE_SCHEMA):
        return _failure("opportunity_not_retained")
    supplied_certificate = opportunity_record.get("certificate")
    if not isinstance(supplied_certificate, Mapping):
        return _failure("opportunity_not_retained")
    snapshot = opportunity_source.read_snapshot(captured_session_id=opportunity_source.session_id)
    matches = [row for row in snapshot["opportunities"]
               if row["certificate"]["boundary_id"] == supplied_certificate.get("boundary_id")]
    if len(matches) != 1 or any(opportunity_record.get(key) != matches[0][key] for key in (
        "certificate", "channel_source", "context_reference", "legal_action_set",
    )):
        return _failure("opportunity_not_retained")
    opportunity = matches[0]
    boundary = opportunity["certificate"]
    if boundary["channel"] not in {"actor_first_person", "simulator_input"}:
        return _failure("channel_not_canonical")
    if not private_source.authenticates(private_information, opportunity_record):
        return _failure("private_information_not_authenticated")
    if (private_information["private_surface_version"] != PRIVATE_SURFACE_VERSION
            or private_information["session_id"] != boundary["session_id"]
            or private_information["battle_id"] != boundary["battle_id"]
            or private_information["actor"] != boundary["actor"]
            or private_information["boundary_id"] != boundary["boundary_id"]
            or private_information["prefix_fingerprint"] != boundary["prefix_fingerprint"]
            or private_information["context_fingerprint"] != boundary["context_fingerprint"]):
        return _failure("private_information_binding_invalid")
    if not command_source.authenticates(submitted_command, boundary):
        return _failure("submitted_command_not_authenticated")
    if any(submitted_command[key] != boundary[expected] for key, expected in (
        ("session_id", "session_id"), ("battle_id", "battle_id"),
        ("actor", "actor"), ("boundary_id", "boundary_id"),
        ("prefix_fingerprint", "prefix_fingerprint"),
        ("context_fingerprint", "context_fingerprint"),
        ("legal_action_set_fingerprint", "legal_action_set_fingerprint"),
    )):
        return _failure("submitted_command_binding_invalid")
    decision = materialize_offline_decision_point(
        boundary_certificate=boundary, channel_source=opportunity["channel_source"],
        context_reference=opportunity["context_reference"],
        legal_action_set=opportunity["legal_action_set"],
        post_boundary_end_sequence=boundary["after_event_sequence"],
        selected_choice_evidence=submitted_command, submitted_command_source=command_source,
    )
    if decision["status"] != "contract_validated":
        return _failure("decision_revalidation_failed")

    if (not isinstance(terminal_target, MappingProxyType)
            or terminal_target.get("session_id") != boundary["session_id"]
            or terminal_target.get("battle_id") != boundary["battle_id"]
            or terminal_source.session_id != boundary["session_id"]
            or terminal_source.battle_id != boundary["battle_id"]):
        return _failure("foreign_terminal_target")
    rebuilt_target = materialize_offline_strategy_terminal_learning_target(
        population_context=terminal_target.get("base_population_context"),
        terminal_source=terminal_source,
    )
    if rebuilt_target.get("status") != "materialized" or rebuilt_target != terminal_target:
        return _failure("terminal_target_reauthentication_failed")
    if not validates_materialized_evaluation_split(evaluation_split):
        return _failure("evaluation_split_invalid")
    memberships = [partition for partition in PARTITIONS
                   for row in evaluation_split["partitions"][partition]["records"]
                   if row["target_record_id"] == terminal_target["target_record_id"] and row == terminal_target]
    if len(memberships) != 1:
        return _failure("target_partition_membership_invalid")
    partition = memberships[0]

    pre = decision["pre_boundary"]
    if (pre["session_id"] != boundary["session_id"] or pre["battle_id"] != boundary["battle_id"]
            or pre["actor"] != boundary["actor"]
            or pre["context_fingerprint"] != boundary["context_fingerprint"]
            or pre["prefix_fingerprint"] != boundary["prefix_fingerprint"]
            or pre["legal_action_set"] != opportunity["legal_action_set"]):
        return _failure("decision_boundary_mismatch")
    private_complete = private_information["completeness"] == "complete_for_v1_supported_private_surface"
    action, action_reason = _resolve_action(
        submitted_command["command_payload"], private_information["private_snapshot"], boundary["actor"],
    ) if private_complete else (None, "actor_private_incomplete")
    if private_complete and action is None and action_reason in {"command_identity_mismatch", "ambiguous_command_identity"}:
        return _failure(action_reason)
    legal = pre["legal_action_set"]
    if action is not None and legal["status"] == "exact" and action["action_id"] not in legal["action_ids"]:
        return _failure("selected_action_not_legal")
    if not private_complete:
        availability = {"availability": "unavailable", "reason": "actor_private_incomplete"}
    elif action is None:
        availability = {"availability": "unavailable", "reason": action_reason}
    elif legal["status"] != "exact":
        availability = {"availability": "unavailable", "reason": "legal_action_set_not_exact"}
    elif pre["choice_opportunity"] == "no_free_choice":
        availability = {"availability": "unavailable", "reason": "no_free_choice"}
    elif terminal_target["target"]["availability"] != "available":
        availability = {"availability": "unavailable", "reason": "terminal_target_unavailable"}
    else:
        availability = {"availability": "available"}

    identity = {
        "decision_id": decision["decision_id"], "boundary_id": boundary["boundary_id"],
        "private_information_id": private_information["private_information_id"],
        "command_id": submitted_command["command_id"],
        "canonical_action_id": action["action_id"] if action is not None else None,
        "terminal_target_record_id": terminal_target["target_record_id"],
        "evaluation_split_id": evaluation_split["evaluation_split_id"],
        "target_policy_version": terminal_target["target_policy_version"],
    }
    return _freeze({
        "status": "materialized", "schema_version": SCHEMA_VERSION,
        "example_id": "offline-choice-outcome-example:" + fingerprint_decision_contract_reference(identity),
        "example_availability": availability,
        "session_id": boundary["session_id"], "battle_id": boundary["battle_id"],
        "decision_id": decision["decision_id"], "boundary_id": boundary["boundary_id"],
        "actor": boundary["actor"], "decision_kind": boundary["decision_kind"],
        "turn_number": boundary["turn_number"], "channel": boundary["channel"],
        "decision_information": {
            "public_pre_boundary": pre,
            "actor_private_snapshot": private_information["private_snapshot"],
            "actor_private_completeness": private_information["completeness"],
            "private_information_id": private_information["private_information_id"],
            "exact_legal_action_set": legal,
        },
        "selected_choice": {
            "direct_command_payload": submitted_command["command_payload"],
            "command_id": submitted_command["command_id"],
            "canonical_action": action,
            "choice_opportunity": pre["choice_opportunity"],
        },
        "outcome": {
            "terminal_target_record_id": terminal_target["target_record_id"],
            "terminal_target": terminal_target["target"],
            "target_policy_version": terminal_target["target_policy_version"],
            "raw_terminal_outcome": terminal_target["raw_terminal_outcome"],
        },
        "evaluation": {
            "evaluation_split_id": evaluation_split["evaluation_split_id"],
            "partition": partition,
        },
        "provenance": {
            "opportunity_source_id": opportunity_source.source_id,
            "private_source_id": private_source.source_id,
            "command_source_id": command_source.source_id,
            "terminal_source_id": terminal_source.source_id,
            "join_basis": "session_id_and_battle_id",
            "limitations": LIMITATIONS,
        },
        "evidence": {
            "opportunity": opportunity_record,
            "private_information": private_information,
            "submitted_command": submitted_command,
            "decision_point": decision,
            "terminal_target": terminal_target,
        },
    })


def _resolve_action(
    command: Mapping[str, Any], private_snapshot: Mapping[str, Any], actor: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    rows = private_snapshot["own_roster"]
    active = [row for row in rows if row["slot_index"] == actor["slot_index"]
              and row["pokemon_id"] == actor["pokemon_id"]]
    if len(active) != 1:
        return None, "active_private_identity_unavailable"
    if command["kind"] == "attack":
        moves = active[0]["moves"]
        if active[0]["move_scope"]["status"] != "exact":
            return None, "exact_move_scope_unavailable"
        by_slot = [move for move in moves if move["move_slot"] == command.get("move_slot")]
        by_id = [move for move in moves if move["move_id"].get("value") == command.get("move_id")]
        if command.get("move_slot") is not None and len(by_slot) != 1:
            return None, "command_move_slot_unresolved"
        if command.get("move_id") is not None and len(by_id) != 1:
            return None, "ambiguous_command_identity"
        selected = by_slot[0] if command.get("move_slot") is not None else by_id[0]
        if command.get("move_slot") is not None and command.get("move_id") is not None and selected != by_id[0]:
            return None, "command_identity_mismatch"
        if selected["move_id"]["availability"] != "available":
            return None, "command_move_identity_unavailable"
        move_id = selected["move_id"]["value"]
        return {
            "kind": "attack", "action_id": f"attack:{move_id}",
            "move_slot": selected["move_slot"], "move_id": move_id,
            "move_slot_basis": "direct_command" if command.get("move_slot") is not None else "actor_private_resolution",
        }, None
    if command["kind"] == "switch":
        if private_snapshot["roster_scope"]["status"] != "exact":
            return None, "exact_roster_scope_unavailable"
        by_slot = [row for row in rows if row["slot_index"] == command.get("incoming_slot_index")]
        by_id = [row for row in rows if row["pokemon_id"] == command.get("incoming_pokemon_id")]
        if command.get("incoming_slot_index") is not None and len(by_slot) != 1:
            return None, "command_switch_slot_unresolved"
        if command.get("incoming_pokemon_id") is not None and len(by_id) != 1:
            return None, "ambiguous_command_identity"
        selected = by_slot[0] if command.get("incoming_slot_index") is not None else by_id[0]
        if command.get("incoming_slot_index") is not None and command.get("incoming_pokemon_id") is not None and selected != by_id[0]:
            return None, "command_identity_mismatch"
        return {
            "kind": "switch", "action_id": f"manual_switch:{selected['pokemon_id']}",
            "incoming_slot_index": selected["slot_index"], "incoming_pokemon_id": selected["pokemon_id"],
            "incoming_slot_basis": "direct_command" if command.get("incoming_slot_index") is not None else "actor_private_resolution",
        }, None
    return None, "command_kind_unresolved"


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
