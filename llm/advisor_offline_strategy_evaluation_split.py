"""Explicit offline episode partitions with exact provenance leakage guards."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import (
    _freeze,
    fingerprint_decision_contract_reference,
)
from llm.advisor_offline_strategy_episode_population_context import COLLECTION_MODES
from llm.advisor_offline_strategy_terminal_learning_target import (
    validates_materialized_terminal_learning_target,
)


SCHEMA_VERSION = "offline-strategy-evaluation-split-v1"
PARTITIONS = ("train", "validation", "test")
LEAKAGE_FIELDS = (
    "set_id", "self_player_cluster_id", "opponent_player_cluster_id", "team_cluster_id",
)
LIMITATIONS = (
    "detached_source_retention_not_independently_reproven",
    "self_and_opponent_player_clusters_checked_in_separate_namespaces",
    "collection_time_not_chronological_authority",
    "external_manifest_label_blindness_not_proven",
    "split_is_not_training_admission",
)


def materialize_offline_strategy_evaluation_split(
    *, target_records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    manifest: Mapping[str, str],
) -> Mapping[str, Any]:
    """Validate owner-supplied assignments without generating any partition."""
    if not isinstance(target_records, (list, tuple)):
        return _failure("target_records_invalid")
    if any(not validates_materialized_terminal_learning_target(row) for row in target_records):
        return _failure("target_record_invalid")
    ordered = sorted(target_records, key=lambda row: row["target_record_id"])
    ids = tuple(row["target_record_id"] for row in ordered)
    if len(set(ids)) != len(ids):
        return _failure("duplicate_target_record_id")
    if not isinstance(manifest, Mapping):
        return _failure("manifest_invalid")
    if set(ids) - set(manifest):
        return _failure("missing_manifest_assignment")
    if set(manifest) - set(ids):
        return _failure("extra_manifest_assignment")
    if any(not isinstance(value, str) or value not in PARTITIONS for value in manifest.values()):
        return _failure("partition_invalid")
    assignments = tuple((record_id, manifest[record_id]) for record_id in ids)

    seen: dict[str, dict[Any, str]] = {
        name: {} for name in (
            "target_record_id", "context_binding_id", "episode_terminal_binding_id",
            "episode_id", "session_battle", *LEAKAGE_FIELDS,
        )
    }
    grouped: dict[str, list[Mapping[str, Any]]] = {partition: [] for partition in PARTITIONS}
    for row in ordered:
        partition = manifest[row["target_record_id"]]
        population = row["base_population_context"]
        binding = population["base_terminal_binding"]
        keys = {
            "target_record_id": row["target_record_id"],
            "context_binding_id": row["context_binding_id"],
            "episode_terminal_binding_id": row["episode_terminal_binding_id"],
            "episode_id": binding["episode_id"],
            "session_battle": (row["session_id"], row["battle_id"]),
        }
        sampling = population["sampling_context"]
        for field in LEAKAGE_FIELDS:
            if sampling[field]["availability"] == "available":
                keys[field] = sampling[field]["value"]
        for name, value in keys.items():
            previous = seen[name].setdefault(value, partition)
            if previous != partition:
                return _failure("cross_partition_" + name)
        grouped[partition].append(row)

    summary = {}
    for partition in PARTITIONS:
        rows = grouped[partition]
        rules: dict[str, dict[str, Any]] = {}
        modes = {mode: 0 for mode in sorted(COLLECTION_MODES)}
        availability = {"available": 0, "unavailable": 0}
        for row in rows:
            population = row["base_population_context"]
            rules_fp = population["rules_context_fingerprint"]
            bucket = rules.setdefault(rules_fp, {
                "rules_context_fingerprint": rules_fp,
                "rules_context": population["rules_context"],
                "record_count": 0,
            })
            if bucket["rules_context"] != population["rules_context"]:
                return _failure("rules_fingerprint_conflict")
            bucket["record_count"] += 1
            modes[population["sampling_context"]["collection_mode"]] += 1
            availability[row["target"]["availability"]] += 1
        summary[partition] = {
            "record_count": len(rows),
            "target_record_ids": tuple(row["target_record_id"] for row in rows),
            "rules_context_buckets": tuple(rules[key] for key in sorted(rules)),
            "collection_mode_counts": modes,
            "target_availability_counts": availability,
            "records": tuple(rows),
        }
    manifest_fingerprint = fingerprint_decision_contract_reference({"assignments": assignments})
    identity = {
        "schema_version": SCHEMA_VERSION,
        "manifest_fingerprint": manifest_fingerprint,
        "target_record_ids": ids,
    }
    return _freeze({
        "status": "validated", "schema_version": SCHEMA_VERSION,
        "evaluation_split_id": "offline-evaluation-split:" + fingerprint_decision_contract_reference(identity),
        "manifest_fingerprint": manifest_fingerprint,
        "manifest_authority": "explicit_external_evaluation_manifest",
        "ordered_assignments": assignments,
        "partitions": summary,
        "leakage_checks": (
            "target_record_id", "context_binding_id", "episode_terminal_binding_id",
            "episode_id", "session_battle", *LEAKAGE_FIELDS,
        ),
        "limitations": LIMITATIONS,
    })


def validates_materialized_evaluation_split(value: Any) -> bool:
    """Rebuild a detached split from its retained records and explicit manifest."""
    if not isinstance(value, MappingProxyType) or value.get("schema_version") != SCHEMA_VERSION:
        return False
    try:
        assignments = value["ordered_assignments"]
        if (not isinstance(assignments, tuple)
                or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in assignments)
                or len({pair[0] for pair in assignments}) != len(assignments)):
            return False
        partitions = value["partitions"]
        if not isinstance(partitions, Mapping) or set(partitions) != set(PARTITIONS):
            return False
        records = tuple(row for partition in PARTITIONS for row in partitions[partition]["records"])
        rebuilt = materialize_offline_strategy_evaluation_split(
            target_records=records, manifest=dict(assignments),
        )
        return rebuilt.get("status") == "validated" and rebuilt == value
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _failure(reason: str) -> Mapping[str, Any]:
    return _freeze({"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": reason})
