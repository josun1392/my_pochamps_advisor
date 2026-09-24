"""Exact train-only occurrence counts over pre-encoding semantic decisions."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_model_feature_semantics import (
    validates_detached_semantic_feature_record,
)


INDEX_SCHEMA = "offline-strategy-train-only-exact-state-action-support-v1"
PROJECTION_SCHEMA = "offline-strategy-exact-state-action-support-projection-v1"
POLICY_VERSION = "exact-semantic-train-occurrence-counts-v1"
SUPPORT_SEMANTICS = "exact_train_decision_record_occurrence_counts"
LIMITATIONS = (
    "decision_record_occurrence_count_not_independent_sample_count",
    "exact_semantic_equality_only_no_similarity_or_oov_collapse",
    "detached_live_source_retention_not_independently_reproven",
)
_STATE_KEYS = ("rules_and_decision", "public_battle", "actor_private", "exact_legal_actions")


def fit_train_only_exact_state_action_support(
    records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any]:
    """Count available train semantic states and selected state-actions only."""
    if not isinstance(records, (list, tuple)) or not records:
        return _index_failure("semantic_records_invalid")
    if any(not validates_detached_semantic_feature_record(row) for row in records):
        return _index_failure("semantic_record_invalid")
    ids = [row["feature_record_id"] for row in records]
    if len(ids) != len(set(ids)):
        return _index_failure("duplicate_feature_record_id")
    split_ids = {row["audit"]["evaluation_split_id"] for row in records}
    if len(split_ids) != 1:
        return _index_failure("mixed_evaluation_split_id")
    train = [row for row in records if row["evaluation_partition"] == "train"]
    eligible = [row for row in train if row["feature_availability"]["availability"] == "available"]
    if not eligible:
        return _index_failure("no_eligible_train_feature_record")
    state_counts: dict[str, int] = {}
    state_action_counts: dict[str, int] = {}
    action_to_state: dict[str, str] = {}
    for row in eligible:
        state = _state_fingerprint(row["model_features"])
        action = row["semantic_feature_fingerprint"]
        if action in action_to_state and action_to_state[action] != state:
            return _index_failure("state_action_fingerprint_conflict")
        action_to_state[action] = state
        state_counts[state] = state_counts.get(state, 0) + 1
        state_action_counts[action] = state_action_counts.get(action, 0) + 1
    state_counts = dict(sorted(state_counts.items()))
    state_action_counts = dict(sorted(state_action_counts.items()))
    action_to_state = dict(sorted(action_to_state.items()))
    identity = {
        "schema_version": INDEX_SCHEMA, "policy_version": POLICY_VERSION,
        "eligible_train_semantic_fingerprints": tuple(sorted(row["semantic_feature_fingerprint"] for row in eligible)),
        "state_counts": state_counts, "state_action_counts": state_action_counts,
        "state_action_to_state": action_to_state,
    }
    return _freeze({
        "status": "fitted", "schema_version": INDEX_SCHEMA,
        "support_index_id": "train-exact-state-action-support:" + fingerprint_decision_contract_reference(identity),
        "support_policy_version": POLICY_VERSION,
        "evaluation_split_id": next(iter(split_ids)),
        "eligible_train_record_count": len(eligible),
        "unavailable_train_record_count": len(train) - len(eligible),
        "distinct_exact_state_count": len(state_counts),
        "distinct_exact_state_action_count": len(state_action_counts),
        "eligible_train_semantic_fingerprints": identity["eligible_train_semantic_fingerprints"],
        "exact_state_counts": state_counts,
        "exact_state_action_counts": state_action_counts,
        "state_action_to_state": action_to_state,
        "support_semantics": SUPPORT_SEMANTICS, "limitations": LIMITATIONS,
    })


def project_exact_state_action_support(
    *, support_index: Mapping[str, Any], semantic_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Project one exact semantic query; zero and unavailable remain distinct."""
    if not _valid_index(support_index):
        return _projection_failure("support_index_invalid")
    if not validates_detached_semantic_feature_record(semantic_record):
        return _projection_failure("semantic_record_invalid")
    if semantic_record["audit"]["evaluation_split_id"] != support_index["evaluation_split_id"]:
        return _projection_failure("evaluation_split_mismatch")
    availability = semantic_record["feature_availability"]
    if availability["availability"] == "unavailable":
        projection = {
            "availability": "unavailable", "reason": "semantic_model_input_unavailable",
            "exact_state_fingerprint": None, "exact_state_action_fingerprint": None,
            "exact_state_train_count": None, "exact_state_action_train_count": None,
            "selected_action": None,
        }
    else:
        features = semantic_record["model_features"]
        state = _state_fingerprint(features)
        action = semantic_record["semantic_feature_fingerprint"]
        projection = {
            "availability": "available", "exact_state_fingerprint": state,
            "exact_state_action_fingerprint": action,
            "exact_state_train_count": support_index["exact_state_counts"].get(state, 0),
            "exact_state_action_train_count": support_index["exact_state_action_counts"].get(action, 0),
            "selected_action": features["selected_action"],
        }
        if projection["exact_state_action_train_count"] > projection["exact_state_train_count"]:
            return _projection_failure("support_count_inconsistent")
    identity = {
        "schema_version": PROJECTION_SCHEMA, "support_index_id": support_index["support_index_id"],
        "projection": projection,
    }
    return _freeze({
        "status": "projected", "schema_version": PROJECTION_SCHEMA,
        "projection_id": "exact-state-action-support-projection:" + fingerprint_decision_contract_reference(identity),
        "support_index_id": support_index["support_index_id"],
        "evaluation_split_id": support_index["evaluation_split_id"],
        **projection, "support_semantics": SUPPORT_SEMANTICS, "limitations": LIMITATIONS,
    })


def _state_fingerprint(features: Mapping[str, Any]) -> str:
    return fingerprint_decision_contract_reference({key: features[key] for key in _STATE_KEYS})


def _valid_index(value: Any) -> bool:
    if (not isinstance(value, MappingProxyType) or set(value) != {
        "status", "schema_version", "support_index_id", "support_policy_version", "evaluation_split_id",
        "eligible_train_record_count", "unavailable_train_record_count", "distinct_exact_state_count",
        "distinct_exact_state_action_count", "eligible_train_semantic_fingerprints", "exact_state_counts",
        "exact_state_action_counts", "state_action_to_state", "support_semantics", "limitations",
    } or value["status"] != "fitted" or value["schema_version"] != INDEX_SCHEMA
            or value["support_policy_version"] != POLICY_VERSION or value["support_semantics"] != SUPPORT_SEMANTICS
            or value["limitations"] != LIMITATIONS or not isinstance(value["evaluation_split_id"], str)
            or not value["evaluation_split_id"]):
        return False
    fingerprints = value["eligible_train_semantic_fingerprints"]
    states = value["exact_state_counts"]
    actions = value["exact_state_action_counts"]
    links = value["state_action_to_state"]
    if (not isinstance(fingerprints, tuple) or not fingerprints or fingerprints != tuple(sorted(fingerprints))
            or not all(isinstance(item, str) and len(item) == 64 for item in fingerprints)
            or not all(isinstance(item, MappingProxyType) for item in (states, actions, links))
            or set(actions) != set(links)
            or any(links[action] not in states for action in actions)
            or any(not isinstance(key, str) or len(key) != 64 or type(count) is not int or count < 1
                   for mapping in (states, actions) for key, count in mapping.items())
            or sum(states.values()) != len(fingerprints) or sum(actions.values()) != len(fingerprints)
            or any(sum(actions[action] for action in actions if links[action] == state) != states[state]
                   for state in states)
            or value["eligible_train_record_count"] != len(fingerprints)
            or type(value["unavailable_train_record_count"]) is not int
            or value["unavailable_train_record_count"] < 0
            or value["distinct_exact_state_count"] != len(states)
            or value["distinct_exact_state_action_count"] != len(actions)):
        return False
    identity = {
        "schema_version": INDEX_SCHEMA, "policy_version": POLICY_VERSION,
        "eligible_train_semantic_fingerprints": fingerprints,
        "state_counts": states, "state_action_counts": actions,
        "state_action_to_state": links,
    }
    return value["support_index_id"] == "train-exact-state-action-support:" + fingerprint_decision_contract_reference(identity)


def _index_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": INDEX_SCHEMA, "reason": reason})


def _projection_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": PROJECTION_SCHEMA, "reason": reason})
