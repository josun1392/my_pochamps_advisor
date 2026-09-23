"""Exact descriptive episode/population coverage, without sufficiency judgments."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import (
    _context as _decision_context_valid,
    _freeze,
    fingerprint_decision_contract_reference,
)
from llm.advisor_offline_strategy_episode_population_context import (
    COLLECTION_MODES,
    COMPETITION_CONTEXTS,
    OPTIONAL_FIELDS,
    validates_materialized_population_context,
)


SCHEMA_VERSION = "offline-strategy-exact-context-support-counts-v1"
QUERY_SCHEMA_VERSION = "offline-strategy-exact-context-support-query-v1"


def materialize_offline_strategy_exact_support_counts(
    records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    """Count validated episode records under exact, declared context fields."""
    if not isinstance(records, (list, tuple)):
        return _failure("records_invalid")
    if any(not validates_materialized_population_context(record) for record in records):
        return _failure("record_invalid")
    ordered = sorted(records, key=lambda row: row["context_binding_id"])
    ids = tuple(row["context_binding_id"] for row in ordered)
    if len(set(ids)) != len(ids):
        return _failure("duplicate_context_binding_id")
    episode_keys = [
        (row["session_id"], row["battle_id"], row["base_terminal_binding"]["episode_id"])
        for row in ordered
    ]
    if len(set(episode_keys)) != len(episode_keys):
        return _failure("conflicting_episode_context")

    modes = {key: 0 for key in sorted(COLLECTION_MODES)}
    competitions = {key: 0 for key in sorted(COMPETITION_CONTEXTS)}
    terminal = {"available": 0, "unavailable": 0}
    declared_results = {"self": 0, "opponent": 0, "tie": 0}
    base_episode_status = {"resolved": 0, "incomplete": 0}
    metadata = {key: {"available": 0, "unavailable": 0} for key in sorted(OPTIONAL_FIELDS)}
    rules: dict[str, dict[str, Any]] = {}
    battle_declarations: dict[tuple[str, str], str] = {}
    resolved = incomplete = 0
    for row in ordered:
        if row["status"] == "resolved":
            resolved += 1
        else:
            incomplete += 1
        base_episode_status[row["base_terminal_binding"]["base_episode_status"]] += 1
        sampling = row["sampling_context"]
        modes[sampling["collection_mode"]] += 1
        competitions[sampling["competition_context"]] += 1
        for field in metadata:
            metadata[field][sampling[field]["availability"]] += 1
        outcome = row["base_terminal_binding"]["terminal_outcome"]
        availability = outcome["availability"]
        terminal[availability] += 1
        if availability == "available":
            battle_key = (row["session_id"], row["battle_id"])
            declaration_id = outcome["evidence_id"]
            previous_declaration = battle_declarations.setdefault(battle_key, declaration_id)
            if previous_declaration != declaration_id:
                return _failure("conflicting_battle_terminal_evidence")
            declared_results[outcome["declared_result"]] += 1
        fingerprint = row["rules_context_fingerprint"]
        bucket = rules.setdefault(fingerprint, {
            "rules_context_fingerprint": fingerprint,
            "rules_context": row["rules_context"],
            "context_binding_ids": [],
        })
        if bucket["rules_context"] != row["rules_context"]:
            return _failure("rules_fingerprint_conflict")
        bucket["context_binding_ids"].append(row["context_binding_id"])
    buckets = tuple({
        "rules_context_fingerprint": fingerprint,
        "rules_context": rules[fingerprint]["rules_context"],
        "record_count": len(rules[fingerprint]["context_binding_ids"]),
        "context_binding_ids": tuple(rules[fingerprint]["context_binding_ids"]),
    } for fingerprint in sorted(rules))
    return _freeze({
        "status": "materialized", "schema_version": SCHEMA_VERSION,
        "inventory_id": "offline-exact-support-counts:" + fingerprint_decision_contract_reference(
            {"context_binding_ids": ids}
        ),
        "context_binding_ids": ids, "records": tuple(ordered),
        "total_records": len(ordered), "resolved_records": resolved,
        "incomplete_records": incomplete,
        "base_episode_status_counts": base_episode_status,
        "rules_context_buckets": buckets,
        "collection_mode_counts": modes,
        "competition_context_counts": competitions,
        "terminal_availability_counts": terminal,
        "declared_result_counts": declared_results,
        "optional_metadata_availability_counts": metadata,
        "limitation": "episode_population_coverage_only_not_state_action_support",
    })


def project_exact_context_support(
    inventory: Mapping[str, Any], *, rules_context: Mapping[str, Any] | None = None,
    collection_mode: str | None = None, competition_context: str | None = None,
) -> Mapping[str, Any]:
    """Return exact matches only; terminal labels are not query dimensions."""
    if not isinstance(inventory, MappingProxyType) or inventory.get("schema_version") != SCHEMA_VERSION:
        return _query_failure("inventory_invalid")
    rebuilt = materialize_offline_strategy_exact_support_counts(inventory.get("records"))
    if rebuilt.get("status") != "materialized" or rebuilt != inventory:
        return _query_failure("inventory_revalidation_failed")
    if rules_context is not None and not _decision_context_valid(rules_context):
        return _query_failure("rules_context_invalid")
    if collection_mode is not None and (not isinstance(collection_mode, str) or collection_mode not in COLLECTION_MODES):
        return _query_failure("collection_mode_invalid")
    if competition_context is not None and (
        not isinstance(competition_context, str) or competition_context not in COMPETITION_CONTEXTS
    ):
        return _query_failure("competition_context_invalid")
    rules_fingerprint = (
        fingerprint_decision_contract_reference(rules_context) if rules_context is not None else None
    )
    matches = tuple(row["context_binding_id"] for row in inventory["records"] if (
        (rules_fingerprint is None or row["rules_context_fingerprint"] == rules_fingerprint)
        and (collection_mode is None or row["sampling_context"]["collection_mode"] == collection_mode)
        and (competition_context is None or row["sampling_context"]["competition_context"] == competition_context)
    ))
    return _freeze({
        "status": "projected", "schema_version": QUERY_SCHEMA_VERSION,
        "inventory_id": inventory["inventory_id"],
        "query": {
            "rules_context": rules_context,
            "rules_context_fingerprint": rules_fingerprint,
            "collection_mode": collection_mode,
            "competition_context": competition_context,
        },
        "matching_record_count": len(matches),
        "matching_context_binding_ids": matches,
    })


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})


def _query_failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": QUERY_SCHEMA_VERSION, "reason": reason})
