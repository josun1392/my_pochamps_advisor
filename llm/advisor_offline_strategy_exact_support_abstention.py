"""Explicit occurrence-count policy over exact semantic train support."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_exact_state_action_support import project_exact_state_action_support


POLICY_SCHEMA = "offline-strategy-exact-support-abstention-policy-v1"
DECISION_SCHEMA = "offline-strategy-exact-support-abstention-decision-v1"
POLICY_VERSION = "explicit-exact-occurrence-minima-v1"
POLICY_AUTHORITY = "explicit_external_exact_support_threshold_policy"
LIMITATIONS = (
    "threshold_pass_does_not_establish_statistical_confidence_or_correctness",
    "decision_record_occurrence_count_not_independent_sample_count",
    "gate_does_not_evaluate_model_quality_or_recommend_an_action",
)
_STATE_REASON = "exact_state_support_below_policy_minimum"
_ACTION_REASON = "exact_state_action_support_below_policy_minimum"
_UNAVAILABLE_REASON = "semantic_model_input_unavailable"


def materialize_exact_support_abstention_policy(
    *, min_exact_state_train_count: int, min_exact_state_action_train_count: int,
) -> Mapping[str, Any]:
    """Record two mandatory caller-selected minima; no threshold is inferred."""
    if type(min_exact_state_train_count) is not int or min_exact_state_train_count < 1:
        return _policy_failure("min_exact_state_train_count_invalid")
    if type(min_exact_state_action_train_count) is not int or min_exact_state_action_train_count < 1:
        return _policy_failure("min_exact_state_action_train_count_invalid")
    identity = {
        "schema_version": POLICY_SCHEMA, "policy_version": POLICY_VERSION,
        "policy_authority": POLICY_AUTHORITY,
        "min_exact_state_train_count": min_exact_state_train_count,
        "min_exact_state_action_train_count": min_exact_state_action_train_count,
    }
    return _freeze({
        "status": "materialized", "schema_version": POLICY_SCHEMA,
        "abstention_policy_id": "exact-support-abstention-policy:" + fingerprint_decision_contract_reference(identity),
        **{key: value for key, value in identity.items() if key != "schema_version"},
        "limitations": LIMITATIONS,
    })


def apply_exact_support_abstention_policy(
    *, policy: Mapping[str, Any], support_index: Mapping[str, Any], semantic_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Project retained exact counts, then apply both explicit minima."""
    if not _valid_policy(policy):
        return _decision_failure("abstention_policy_invalid")
    projection = project_exact_state_action_support(
        support_index=support_index, semantic_record=semantic_record,
    )
    if projection.get("status") != "projected":
        return _decision_failure("support_projection_failed:" + str(projection.get("reason")))
    state_count = projection["exact_state_train_count"]
    action_count = projection["exact_state_action_train_count"]
    if projection["availability"] == "unavailable":
        result = "abstain"
        reasons = (_UNAVAILABLE_REASON,)
    else:
        reasons = tuple(reason for condition, reason in (
            (state_count < policy["min_exact_state_train_count"], _STATE_REASON),
            (action_count < policy["min_exact_state_action_train_count"], _ACTION_REASON),
        ) if condition)
        result = "abstain" if reasons else "allow_learned_estimate"
    identity = {
        "schema_version": DECISION_SCHEMA, "policy_id": policy["abstention_policy_id"],
        "support_projection_id": projection["projection_id"],
        "support_index_id": projection["support_index_id"],
        "gate_result": result, "reasons": reasons,
    }
    return _freeze({
        "status": "decided", "schema_version": DECISION_SCHEMA,
        "abstention_decision_id": "exact-support-abstention-decision:" + fingerprint_decision_contract_reference(identity),
        "abstention_policy_id": policy["abstention_policy_id"],
        "support_index_id": projection["support_index_id"],
        "evaluation_split_id": projection["evaluation_split_id"],
        "gate_result": result, "reasons": reasons,
        "exact_state_train_count": state_count,
        "exact_state_action_train_count": action_count,
        "min_exact_state_train_count": policy["min_exact_state_train_count"],
        "min_exact_state_action_train_count": policy["min_exact_state_action_train_count"],
        "exact_state_fingerprint": projection["exact_state_fingerprint"],
        "exact_state_action_fingerprint": projection["exact_state_action_fingerprint"],
        "support_projection": projection,
        "gate_semantics": "explicit_occurrence_count_policy_satisfied_only" if not reasons
                          else "explicit_occurrence_count_policy_not_satisfied",
        "limitations": LIMITATIONS,
    })


def _valid_policy(value: Any) -> bool:
    if (not isinstance(value, MappingProxyType) or set(value) != {
        "status", "schema_version", "abstention_policy_id", "policy_version", "policy_authority",
        "min_exact_state_train_count", "min_exact_state_action_train_count", "limitations",
    } or value["status"] != "materialized" or value["schema_version"] != POLICY_SCHEMA
            or value["policy_version"] != POLICY_VERSION or value["policy_authority"] != POLICY_AUTHORITY
            or value["limitations"] != LIMITATIONS):
        return False
    state = value["min_exact_state_train_count"]
    action = value["min_exact_state_action_train_count"]
    if type(state) is not int or state < 1 or type(action) is not int or action < 1:
        return False
    identity = {
        "schema_version": POLICY_SCHEMA, "policy_version": POLICY_VERSION,
        "policy_authority": POLICY_AUTHORITY,
        "min_exact_state_train_count": state,
        "min_exact_state_action_train_count": action,
    }
    return value["abstention_policy_id"] == "exact-support-abstention-policy:" + fingerprint_decision_contract_reference(identity)


def _policy_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": POLICY_SCHEMA, "reason": reason})


def _decision_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": DECISION_SCHEMA, "reason": reason})
