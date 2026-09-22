"""Strict detached current-paralysis action-opportunity prediction for C5.

This owner exposes only the canonical Champions full-paralysis opportunity:
1/8 cancellation and 7/8 execution.  It binds to an already-created historical
predictive action link and never creates a second real-action identity.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority,
    freeze_runtime_strategy_d0,
)


SCHEMA_VERSION = "detached-current-action-paralysis-opportunity-authority-v1"
PROVENANCE = "historical_action_link_bound_current_paralysis_opportunity_v1"
_PREDICTION_KIND = "action_opportunity_execution"


def materialize_current_action_paralysis_opportunity_authority(
    *,
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze exact 1/8 vs 7/8 branches for one currently-paralyzed action."""
    from llm.advisor_detached_observed_rng_reconciliation import (
        validate_historical_predictive_action_binding,
    )

    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return _result(checked.get("status", "rejected"), checked.get("reason", "historical_predictive_binding_invalid"))

    if (
        not isinstance(runtime_snapshot, Mapping)
        or runtime_snapshot.get("status") != "runtime_snapshot_ready"
        or runtime_snapshot.get("session_id") != checked["session_id"]
        or runtime_snapshot.get("state_fingerprint") != checked["source_runtime_fingerprint"]
    ):
        return _result("rejected", "paralysis_opportunity_runtime_binding_mismatch")

    d0 = freeze_runtime_strategy_d0(
        runtime_snapshot=runtime_snapshot, decision_owner=checked["decision_owner"],
    )
    if d0.get("status") != "resolved":
        return _result(d0.get("status", "rejected"), d0.get("reason", "paralysis_opportunity_d0_unavailable"))
    if (
        d0.get("session_id") != checked["session_id"]
        or d0.get("source_runtime_fingerprint") != checked["source_runtime_fingerprint"]
        or d0.get("strategy_preview_fingerprint") != checked["source_branch_fingerprint"]
        or d0.get("decision_owner") != checked["decision_owner"]
        or d0.get("active_owners", {}).get(checked["actor"]["side"]) != checked["actor"]
        or d0.get("active_owners", {}).get(checked["target"]["side"]) != checked["target"]
    ):
        return _result("rejected", "paralysis_opportunity_predictive_binding_mismatch")

    condition = freeze_runtime_current_condition_authority(
        strategy_d0=d0, runtime_snapshot=runtime_snapshot, owner=checked["actor"],
    )
    if condition.get("status") != "resolved":
        return _result(condition.get("status", "rejected"), condition.get("reason", "current_condition_authority_unavailable"))
    state = condition.get("condition")
    if not isinstance(state, Mapping) or state.get("status") == "unknown":
        return _result("incomplete", "current_condition_unknown")
    if state.get("status") == "known_none" or (
        state.get("status") == "known_present" and state.get("condition") != "paralysis"
    ):
        return {
            "status": "not_applicable",
            "schema_version": SCHEMA_VERSION,
            "source_action_id": checked["source_action_id"],
            "move_id": checked["move_id"],
            "reason": "actor_not_currently_paralyzed",
            "current_condition_authority": deepcopy(condition),
            "provenance": PROVENANCE,
        }
    if state != {
        "status": "known_present",
        "condition": "paralysis",
        "provenance": "runtime_current_condition_observed",
    }:
        return _result("rejected", "current_paralysis_authority_malformed")

    base = {
        "schema_version": SCHEMA_VERSION,
        "prediction_kind": _PREDICTION_KIND,
        "session_id": checked["session_id"],
        "turn_number": checked["turn_number"],
        "source_action_id": checked["source_action_id"],
        "action_link_id": checked["action_link_id"],
        "actor": deepcopy(checked["actor"]),
        "target": deepcopy(checked["target"]),
        "move_id": checked["move_id"],
        "candidate_id": checked["candidate_id"],
        "source_runtime_fingerprint": checked["source_runtime_fingerprint"],
        "source_branch_fingerprint": checked["source_branch_fingerprint"],
        "decision_owner": deepcopy(checked["decision_owner"]),
        "source_predictive_ledger_fingerprint": checked["predictive_ledger_fingerprint"],
        "historical_predictive_binding": deepcopy(checked),
        "current_condition_authority": deepcopy(condition),
        "root_probability_mass": _fd(Fraction(1, 1)),
        "provenance": PROVENANCE,
    }
    branches = (
        _branch(base, "fully_paralyzed", executes=False, probability=Fraction(1, 8)),
        _branch(base, "executes", executes=True, probability=Fraction(7, 8)),
    )
    fingerprint_payload = {**base, "branches": branches}
    fingerprint = hashlib.sha256(_canonical_bytes(fingerprint_payload)).hexdigest()
    return {
        "status": "resolved",
        **deepcopy(base),
        "branches": branches,
        "prediction_fingerprint": fingerprint,
        "prediction_identity": {
            "schema_version": SCHEMA_VERSION,
            "fingerprint": fingerprint,
            "source_action_id": checked["source_action_id"],
            "move_id": checked["move_id"],
        },
    }


def validate_current_action_paralysis_opportunity_authority(
    *,
    authority: Mapping[str, Any],
    predictive_binding: Mapping[str, Any],
    predictive_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate a retained historical authority without reconstructing it."""
    from llm.advisor_detached_observed_rng_reconciliation import (
        validate_historical_predictive_action_binding,
    )

    checked = validate_historical_predictive_action_binding(
        binding=predictive_binding, predictive_ledger=predictive_ledger,
    )
    if checked.get("status") != "resolved":
        return checked
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved" or authority.get("schema_version") != SCHEMA_VERSION:
        return _result("rejected", "paralysis_opportunity_authority_invalid")

    required_equal = {
        "session_id": checked["session_id"],
        "turn_number": checked["turn_number"],
        "source_action_id": checked["source_action_id"],
        "action_link_id": checked["action_link_id"],
        "actor": checked["actor"],
        "target": checked["target"],
        "move_id": checked["move_id"],
        "candidate_id": checked["candidate_id"],
        "source_runtime_fingerprint": checked["source_runtime_fingerprint"],
        "source_branch_fingerprint": checked["source_branch_fingerprint"],
        "decision_owner": checked["decision_owner"],
        "source_predictive_ledger_fingerprint": checked["predictive_ledger_fingerprint"],
        "historical_predictive_binding": checked,
        "root_probability_mass": _fd(Fraction(1, 1)),
        "prediction_kind": _PREDICTION_KIND,
        "provenance": PROVENANCE,
    }
    if any(authority.get(key) != value for key, value in required_equal.items()):
        return _result("rejected", "paralysis_opportunity_authority_binding_mismatch")

    condition = authority.get("current_condition_authority")
    if (
        not isinstance(condition, Mapping)
        or condition.get("status") != "resolved"
        or condition.get("session_id") != checked["session_id"]
        or condition.get("source_runtime_fingerprint") != checked["source_runtime_fingerprint"]
        or condition.get("source_branch_fingerprint") != checked["source_branch_fingerprint"]
        or condition.get("owner") != checked["actor"]
        or condition.get("condition") != {
            "status": "known_present",
            "condition": "paralysis",
            "provenance": "runtime_current_condition_observed",
        }
    ):
        return _result("rejected", "paralysis_opportunity_condition_binding_mismatch")

    branches = authority.get("branches")
    expected = (
        _branch(required_equal, "fully_paralyzed", executes=False, probability=Fraction(1, 8)),
        _branch(required_equal, "executes", executes=True, probability=Fraction(7, 8)),
    )
    if branches != expected:
        return _result("rejected", "paralysis_opportunity_branch_contract_mismatch")
    if sum((_fraction(row.get("probability")) or Fraction() for row in branches), Fraction()) != Fraction(1, 1):
        return _result("rejected", "paralysis_opportunity_root_mass_invalid")

    payload = {key: deepcopy(authority[key]) for key in (
        "schema_version", "prediction_kind", "session_id", "turn_number",
        "source_action_id", "action_link_id", "actor", "target", "move_id",
        "candidate_id", "source_runtime_fingerprint", "source_branch_fingerprint",
        "decision_owner", "source_predictive_ledger_fingerprint",
        "historical_predictive_binding", "current_condition_authority",
        "root_probability_mass", "provenance",
    )}
    payload["branches"] = deepcopy(branches)
    fingerprint = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    if authority.get("prediction_fingerprint") != fingerprint or authority.get("prediction_identity") != {
        "schema_version": SCHEMA_VERSION,
        "fingerprint": fingerprint,
        "source_action_id": checked["source_action_id"],
        "move_id": checked["move_id"],
    }:
        return _result("rejected", "paralysis_opportunity_prediction_fingerprint_mismatch")
    return deepcopy(dict(authority))


def _branch(base: Mapping[str, Any], kind: str, *, executes: bool, probability: Fraction) -> dict[str, Any]:
    source_action_id = base.get("source_action_id")
    move_id = base.get("move_id")
    actor = base.get("actor")
    return {
        "branch_id": f"{source_action_id}:paralysis:{kind}",
        "state": "cancelled_due_to_paralysis" if not executes else "executed",
        "kind": kind,
        "executes": executes,
        "probability": _fd(probability),
        "source_action_id": source_action_id,
        "move_id": move_id,
        "actor": deepcopy(actor),
        "prediction_kind": _PREDICTION_KIND,
    }


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _fd(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any) -> Fraction | None:
    if not isinstance(value, Mapping):
        return None
    numerator, denominator = value.get("numerator"), value.get("denominator")
    if isinstance(numerator, bool) or isinstance(denominator, bool) or not isinstance(numerator, int) or not isinstance(denominator, int) or denominator <= 0:
        return None
    try:
        return Fraction(numerator, denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
