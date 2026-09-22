"""C5 adapters for existing exact full-paralysis predictive paths.

These adapters never create paralysis probabilities.  They authenticate and
normalize exact 1/8 / 7/8 branches already owned by existing predictive
artifacts while preserving their original branch identities and causal source.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping

from llm.advisor_detached_observed_rng_reconciliation import (
    validate_historical_predictive_action_binding,
)

SCHEMA_VERSION = "detached-existing-paralysis-opportunity-reconciliation-adapter-v1"
PROVENANCE = "c5_existing_paralysis_opportunity_identity_adapter_v1"
_SECOND_SCHEMA = "detached-intermediate-paralysis-second-action-authority-v1"
_CHARGE_SCHEMAS = {
    "standard-charge-terminal-attack-kernel-v1",
    "geomancy-charge-status-terminal-execution-v1",
}


def adapt_intermediate_paralysis_second_action_opportunity(
    *, source_authority: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    if (
        not isinstance(source_authority, Mapping)
        or source_authority.get("status") != "resolved"
        or source_authority.get("schema_version") != _SECOND_SCHEMA
        or source_authority.get("hypothetical") is not True
        or source_authority.get("horizon") != "immediate_action_pair"
        or source_authority.get("provenance") != "exact_intermediate_paralysis_second_action_consumer_v1"
    ):
        return _r("rejected", "second_action_source_authority_invalid")
    if (
        source_authority.get("session_id") != checked["session_id"]
        or source_authority.get("source_runtime_fingerprint") != checked["source_runtime_fingerprint"]
        or source_authority.get("source_branch_fingerprint") != checked["source_branch_fingerprint"]
        or source_authority.get("predictive_actor") != checked["actor"]
        or source_authority.get("predictive_target") != checked["target"]
        or source_authority.get("move_id") != checked["move_id"]
    ):
        return _r("rejected", "second_action_historical_action_binding_mismatch")
    first_leaf = source_authority.get("source_first_action_leaf_id")
    intermediate = source_authority.get("intermediate_state_id")
    if (
        not isinstance(first_leaf, str) or not first_leaf
        or not isinstance(intermediate, str) or not intermediate
        or not intermediate.endswith(":" + first_leaf)
    ):
        return _r("rejected", "second_action_causal_provenance_missing")
    builder = source_authority.get("builder_inputs")
    predictive_d0 = builder.get("strategy_d0") if isinstance(builder, Mapping) else None
    predictive_snapshot = builder.get("runtime_snapshot") if isinstance(builder, Mapping) else None
    if (
        not isinstance(predictive_d0, Mapping)
        or predictive_d0.get("status") != "resolved"
        or predictive_d0.get("decision_owner") != checked["actor"]
        or not isinstance(predictive_snapshot, Mapping)
        or predictive_snapshot.get("status") != "runtime_snapshot_ready"
        or predictive_snapshot.get("session_id") != checked["session_id"]
        or builder.get("attacker") != checked["actor"]
        or builder.get("target") != checked["target"]
    ):
        return _r("rejected", "second_action_predictive_view_binding_mismatch")
    branches = source_authority.get("second_action_execution_branches")
    expected = (
        ("second_action:fully_paralyzed", "cancelled_due_to_paralysis", False, Fraction(1, 8)),
        ("second_action:can_act_after_paralysis", "executed", True, Fraction(7, 8)),
    )
    normalized = _normalize_existing_branches(
        branches, expected=expected, id_key="execution_branch_id",
        probability_key="conditional_probability",
    )
    if isinstance(normalized, str):
        return _r("rejected", normalized)
    source_fp = _fingerprint(source_authority)
    return _adapter(
        checked=checked, source_kind="hypothetical_second_action_after_paralysis",
        source_schema=_SECOND_SCHEMA, source_fingerprint=source_fp,
        source_artifact=source_authority, branches=normalized,
        causal_provenance={
            "source_first_action_leaf_id": first_leaf,
            "intermediate_state_id": intermediate,
            "source_prediction_decision_owner": deepcopy(source_authority.get("decision_owner")),
        },
        direct_damage_execution_evidence_allowed=True,
        accuracy_miss_execution_evidence_allowed=True,
    )


def adapt_standard_charge_terminal_paralysis_opportunity(
    *, terminal_execution: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    if (
        not isinstance(terminal_execution, Mapping)
        or terminal_execution.get("status") != "resolved"
        or terminal_execution.get("schema_version") not in _CHARGE_SCHEMAS
        or terminal_execution.get("terminal_probability_mass") != _fd(Fraction(1, 1))
    ):
        return _r("rejected", "charge_terminal_source_artifact_invalid")
    gate = terminal_execution.get("pre_action_gate")
    if not isinstance(gate, Mapping) or gate.get("status") != "resolved" or gate.get("outcome") != "branches":
        return _r("rejected", "charge_terminal_pre_action_gate_invalid")
    normalized = _normalize_existing_branches(
        gate.get("branches"),
        expected=(
            ("cancelled_due_to_paralysis", "cancelled_due_to_paralysis", False, Fraction(1, 8)),
            ("executes_after_paralysis", "executed", True, Fraction(7, 8)),
        ),
        id_key="kind", probability_key="probability",
    )
    if isinstance(normalized, str):
        return _r("rejected", normalized)

    leaves = terminal_execution.get("terminal_leaves")
    if not isinstance(leaves, (tuple, list)) or not leaves:
        return _r("rejected", "charge_terminal_leaves_missing")
    provenance = leaves[0].get("provenance") if isinstance(leaves[0], Mapping) else None
    if not isinstance(provenance, Mapping):
        return _r("rejected", "charge_terminal_leaf_provenance_missing")
    if (
        provenance.get("attacker") != checked["actor"]
        or provenance.get("target") != checked["target"]
        or provenance.get("move_id") != checked["move_id"]
        or provenance.get("session_id", checked["session_id"]) != checked["session_id"]
    ):
        return _r("rejected", "charge_terminal_historical_action_binding_mismatch")
    for key in ("source_runtime_fingerprint", "source_branch_fingerprint"):
        if key in provenance and provenance.get(key) != checked[key]:
            return _r("rejected", "charge_terminal_historical_action_binding_mismatch")
    if "decision_owner" in provenance and provenance.get("decision_owner") != checked["decision_owner"]:
        return _r("rejected", "charge_terminal_historical_action_binding_mismatch")

    execution_contract = terminal_execution.get("execution_contract")
    execution_authority = (
        execution_contract.get("caller_action_authority")
        if isinstance(execution_contract, Mapping)
        else terminal_execution.get("execution_authority")
    )
    if not isinstance(execution_authority, Mapping):
        return _r("rejected", "charge_terminal_execution_authority_missing")
    action_id = None
    execution_mode = None
    lifecycle = None
    caller_kind = None
    action_id = _terminal_action_id_from_leaves(leaves)
    if terminal_execution["schema_version"] == "standard-charge-terminal-attack-kernel-v1":
        execution_mode, lifecycle, caller_kind, original_action_id, caller_fingerprint = _charge_caller_context(execution_authority)
    else:
        execution_mode, lifecycle, caller_kind, original_action_id, caller_fingerprint = _geomancy_caller_context(execution_authority, execution_contract)
    if (
        not isinstance(action_id, str) or not action_id
        or not isinstance(execution_mode, str) or not isinstance(caller_kind, str)
        or original_action_id != checked["candidate_id"]
        or not isinstance(caller_fingerprint, str)
        or caller_fingerprint != checked["source_runtime_fingerprint"]
    ):
        return _r("rejected", "charge_terminal_caller_identity_unavailable")
    if execution_mode == "forced_turn_two_continuation":
        if (
            not isinstance(lifecycle, Mapping)
            or lifecycle.get("status") != "resolved"
            or lifecycle.get("actor") != checked["actor"]
            or lifecycle.get("move_id") != checked["move_id"]
            or lifecycle.get("action_id") != checked["candidate_id"]
            or lifecycle.get("turn_two_continuation_required") is not True
        ):
            return _r("rejected", "charge_terminal_lifecycle_provenance_invalid")

    status_only = terminal_execution["schema_version"] == "geomancy-charge-status-terminal-execution-v1"
    source_fp = _fingerprint(terminal_execution)
    return _adapter(
        checked=checked, source_kind="standard_charge_terminal_execution",
        source_schema=terminal_execution["schema_version"],
        source_fingerprint=source_fp, source_artifact=terminal_execution,
        branches=normalized,
        causal_provenance={
            "terminal_action_id": action_id,
            "execution_mode": execution_mode,
            "caller_kind": caller_kind,
            "charge_lifecycle": deepcopy(lifecycle),
        },
        direct_damage_execution_evidence_allowed=not status_only,
        accuracy_miss_execution_evidence_allowed=not status_only,
    )


def validate_existing_paralysis_opportunity_adapter(
    *, adapter: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(adapter, Mapping) or adapter.get("status") != "resolved" or adapter.get("schema_version") != SCHEMA_VERSION:
        return _r("rejected", "existing_paralysis_adapter_invalid")
    kind = adapter.get("source_adapter_kind")
    source = adapter.get("source_artifact")
    if kind == "hypothetical_second_action_after_paralysis":
        expected = adapt_intermediate_paralysis_second_action_opportunity(
            source_authority=source, predictive_binding=predictive_binding,
            predictive_ledger=predictive_ledger,
        )
    elif kind == "standard_charge_terminal_execution":
        expected = adapt_standard_charge_terminal_paralysis_opportunity(
            terminal_execution=source, predictive_binding=predictive_binding,
            predictive_ledger=predictive_ledger,
        )
    else:
        return _r("rejected", "existing_paralysis_adapter_kind_invalid")
    if expected.get("status") != "resolved":
        return expected
    if dict(adapter) != expected:
        return _r("rejected", "existing_paralysis_adapter_fingerprint_or_binding_mismatch")
    return deepcopy(expected)


def _adapter(
    *, checked: Mapping[str, Any], source_kind: str, source_schema: str,
    source_fingerprint: str, source_artifact: Mapping[str, Any],
    branches: tuple[dict[str, Any], ...], causal_provenance: Mapping[str, Any],
    direct_damage_execution_evidence_allowed: bool,
    accuracy_miss_execution_evidence_allowed: bool,
) -> dict[str, Any]:
    identity_seed = {
        "source_adapter_kind": source_kind,
        "source_schema_version": source_schema,
        "source_artifact_fingerprint": source_fingerprint,
        "source_action_id": checked["source_action_id"],
        "causal_provenance": causal_provenance,
        "branches": branches,
    }
    fingerprint = hashlib.sha256(_canonical(identity_seed)).hexdigest()
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "prediction_kind": "action_opportunity_execution",
        **{key: deepcopy(checked[key]) for key in (
            "session_id", "turn_number", "source_action_id", "action_link_id",
            "actor", "target", "move_id", "candidate_id",
            "source_runtime_fingerprint", "source_branch_fingerprint",
            "decision_owner", "predictive_ledger_fingerprint",
        )},
        "source_adapter_kind": source_kind,
        "source_schema_version": source_schema,
        "source_artifact_fingerprint": source_fingerprint,
        "source_artifact": deepcopy(dict(source_artifact)),
        "causal_provenance": deepcopy(dict(causal_provenance)),
        "branches": branches,
        "root_probability_mass": _fd(Fraction(1, 1)),
        "direct_damage_execution_evidence_allowed": direct_damage_execution_evidence_allowed,
        "accuracy_miss_execution_evidence_allowed": accuracy_miss_execution_evidence_allowed,
        "prediction_fingerprint": fingerprint,
        "prediction_identity": {
            "schema_version": SCHEMA_VERSION,
            "fingerprint": fingerprint,
            "source_action_id": checked["source_action_id"],
            "move_id": checked["move_id"],
            "source_artifact_fingerprint": source_fingerprint,
        },
        "provenance": PROVENANCE,
    }


def _normalize_existing_branches(value: Any, *, expected, id_key: str, probability_key: str):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return "existing_paralysis_source_branch_shape_invalid"
    out = []
    for row, (branch_id, state, executes, probability) in zip(value, expected):
        if (
            not isinstance(row, Mapping)
            or row.get(id_key) != branch_id
            or row.get("state", state) != state
            or row.get("executes", state == "executed") is not executes
            or _fraction(row.get(probability_key)) != probability
        ):
            return "existing_paralysis_source_branch_contract_mismatch"
        out.append({
            "branch_id": row[id_key],
            "state": state,
            "executes": executes,
            "probability": deepcopy(row[probability_key]),
            "source_branch": deepcopy(dict(row)),
        })
    if sum((_fraction(row["probability"]) for row in out), Fraction()) != Fraction(1, 1):
        return "existing_paralysis_source_root_mass_invalid"
    return tuple(out)


def _terminal_action_id_from_leaves(leaves: Any) -> str | None:
    ids = {leaf.get("candidate_id") for leaf in leaves if isinstance(leaf, Mapping)}
    return next(iter(ids)) if len(ids) == 1 and isinstance(next(iter(ids)), str) else None


def _charge_caller_context(authority: Mapping[str, Any]):
    schema = authority.get("schema_version")
    if authority.get("execution_grant") == "authenticated_standard_charge_turn_two_only":
        return (
            "forced_turn_two_continuation",
            authority.get("original_charge_lifecycle"),
            "forced_turn_two_continuation",
            authority.get("original_charge_action_id"),
            authority.get("source_next_decision_fingerprint"),
        )
    if schema == "runtime-d0-standard-charge-power-herb-skip-execution-authority-v1":
        return (
            "power_herb_current_turn_skip",
            authority.get("canonical_charge_lifecycle_authority"),
            "power_herb_current_turn_skip",
            authority.get("action_id"),
            authority.get("source_runtime_fingerprint"),
        )
    if schema == "runtime-d0-solar-weather-skip-execution-authority-v1":
        return (
            "weather_current_turn_skip",
            authority.get("canonical_charge_lifecycle_authority"),
            "weather_current_turn_skip",
            authority.get("action_id"),
            authority.get("source_runtime_fingerprint"),
        )
    return None, None, None, None, None


def _geomancy_caller_context(authority: Mapping[str, Any], contract: Any):
    if authority.get("execution_grant") == "authenticated_standard_charge_turn_two_only":
        return (
            "forced_turn_two_continuation",
            authority.get("original_charge_lifecycle"),
            "forced_turn_two_continuation",
            authority.get("original_charge_action_id"),
            authority.get("source_next_decision_fingerprint"),
        )
    if authority.get("schema_version") == "runtime-d0-geomancy-power-herb-skip-execution-authority-v1":
        return (
            "power_herb_current_turn_skip",
            authority.get("canonical_charge_lifecycle_authority"),
            "power_herb_current_turn_skip",
            authority.get("action_id"),
            authority.get("source_runtime_fingerprint"),
        )
    if isinstance(contract, Mapping) and contract.get("execution_mode") == "power_herb_current_turn_skip":
        return (
            "power_herb_current_turn_skip",
            authority.get("canonical_charge_lifecycle_authority"),
            "power_herb_current_turn_skip",
            contract.get("action_id"),
            contract.get("source_state_fingerprint"),
        )
    return None, None, None, None, None


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping):
        return None
    n, d = value.get("numerator"), value.get("denominator")
    if isinstance(n, bool) or isinstance(d, bool) or not isinstance(n, int) or not isinstance(d, int) or d <= 0:
        return None
    try:
        return Fraction(n, d)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _fd(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=list).encode("ascii")


def _r(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
