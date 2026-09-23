"""Read-only, offline state-action features from existing strict strategy evidence.

This module assigns no utility and has no live recommendation caller.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_exact_outcome_descriptive_metrics import project_exact_outcome_descriptive_metrics
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "offline-learned-strategy-state-action-features-v1"
_STRATEGY_SCHEMA = "deterministic-strategy-orchestration-result-v1"
_CANDIDATE_SCHEMA = "deterministic-strategy-candidate-evidence-v1"
_LEDGER_SCHEMA = "exact-predictive-outcome-ledger-v1"
_METRICS_SCHEMA = "exact-outcome-descriptive-metrics-v1"
_HORIZON = "immediate_action_consequence"


def materialize_offline_learned_strategy_feature_rows(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    strategy_result: Mapping[str, Any],
    exact_outcome_ledgers: Mapping[str, Mapping[str, Any]],
    descriptive_metrics: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Return sorted, deeply read-only rows or a fail-closed result."""
    if not isinstance(strategy_d0, Mapping) or not isinstance(runtime_snapshot, Mapping):
        return _failure("rejected", "invalid_strategy_source")
    freshness = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if freshness.get("status") != "current":
        return _failure("rejected", freshness.get("reason", "strategy_d0_not_current"))
    if (
        not isinstance(strategy_result, Mapping)
        or strategy_result.get("schema_version") != _STRATEGY_SCHEMA
        or strategy_result.get("status") not in {"resolved", "incomplete_comparison_set"}
        or strategy_result.get("session_id") != strategy_d0["session_id"]
        or strategy_result.get("decision_branch_fingerprint") != strategy_d0["strategy_preview_fingerprint"]
        or strategy_result.get("decision_owner") != strategy_d0["decision_owner"]
    ):
        return _failure("rejected", "strategy_result_provenance_mismatch")
    candidates = strategy_result.get("candidates")
    if (
        not isinstance(candidates, (tuple, list)) or not candidates
        or not isinstance(exact_outcome_ledgers, Mapping)
        or not isinstance(descriptive_metrics, Mapping)
    ):
        return _failure("rejected", "candidate_inputs_invalid")
    by_id: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        if (
            not isinstance(candidate, Mapping)
            or candidate.get("schema_version") != _CANDIDATE_SCHEMA
            or not isinstance(candidate.get("candidate_id"), str)
            or not candidate["candidate_id"]
            or candidate.get("action_type") not in {"attack", "manual_switch"}
            or candidate.get("evidence_class") not in {
                "exact_outcome", "guaranteed_facts", "hit_miss_uncertainty", "incomplete",
            }
            or (
                isinstance(candidate.get("facts"), Mapping)
                and candidate["facts"].get("candidate_id") != candidate["candidate_id"]
            )
            or candidate["candidate_id"] in by_id
        ):
            return _failure("rejected", "candidate_evidence_invalid")
        by_id[candidate["candidate_id"]] = candidate
    if set(exact_outcome_ledgers) - set(by_id) or set(descriptive_metrics) - set(by_id):
        return _failure("rejected", "foreign_candidate_evidence")

    provenance = {
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": strategy_d0["decision_owner"],
    }
    rows = []
    for candidate_id in sorted(by_id):
        candidate = by_id[candidate_id]
        ledger = exact_outcome_ledgers.get(candidate_id)
        metrics = descriptive_metrics.get(candidate_id)
        result = _candidate_row(candidate, ledger, metrics, provenance)
        if result["status"] == "rejected":
            return _failure("rejected", result["reason"], candidate_id=candidate_id)
        rows.append(result)
    return _freeze({
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "provenance": provenance, "rows": tuple(rows),
    })


def _candidate_row(
    candidate: Mapping[str, Any],
    ledger: Any,
    metrics: Any,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = candidate["candidate_id"]
    action_type = candidate["action_type"]
    readiness = candidate.get("execution_readiness")
    if readiness is not None and (not isinstance(readiness, str) or not readiness):
        return _failure("rejected", "execution_readiness_invalid")
    fields = {
        "execution_readiness": _available(readiness) if readiness is not None else _unavailable("readiness_not_established"),
        "terminal_probability_mass": _unavailable("exact_ledger_unavailable"),
        "target_ko_probability": _unavailable("descriptive_metrics_unavailable"),
        "own_faint_probability": _unavailable("descriptive_metrics_unavailable"),
        "target_final_hp_distribution": _unavailable("descriptive_metrics_unavailable"),
        "own_final_hp_distribution": _unavailable("descriptive_metrics_unavailable"),
        "guaranteed_target_ko": _unavailable("descriptive_metrics_unavailable"),
        "guaranteed_self_faint": _unavailable("descriptive_metrics_unavailable"),
    }
    row = {
        "status": "incomplete", "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id, "action_type": action_type,
        "evidence_class": candidate["evidence_class"],
        "provenance": {**provenance, "candidate_id": candidate_id},
        "features": fields,
    }
    if ledger is None:
        if metrics is not None:
            return _failure("rejected", "metrics_without_ledger")
        return row
    if not isinstance(ledger, Mapping):
        return _failure("rejected", "ledger_invalid")
    if ledger.get("status") in {"incomplete", "unsupported"}:
        if (
            metrics is not None
            or ledger.get("candidate_id") != candidate_id
            or ledger.get("action_type") != action_type
            or not _bound(ledger.get("bindings"), provenance, candidate_id, action_type)
        ):
            return _failure("rejected", "incomplete_ledger_binding_invalid")
        return row
    if (
        ledger.get("status") != "evaluable"
        or ledger.get("schema_version") != _LEDGER_SCHEMA
        or ledger.get("horizon") != _HORIZON
        or ledger.get("candidate_id") != candidate_id
        or ledger.get("action_type") != action_type
        or not _bound(ledger.get("bindings"), provenance, candidate_id, action_type)
    ):
        return _failure("rejected", "ledger_provenance_mismatch")
    projected = project_exact_outcome_descriptive_metrics(ledger=ledger)
    if projected.get("status") != "resolved":
        return _failure("rejected", projected.get("reason", "ledger_invalid"))
    fields["terminal_probability_mass"] = _available(ledger["terminal_probability_mass"])
    if metrics is None or (isinstance(metrics, Mapping) and metrics.get("status") in {"incomplete", "unsupported"}):
        if isinstance(metrics, Mapping) and (
            metrics.get("schema_version") != _METRICS_SCHEMA
            or (metrics.get("candidate_id") is not None and metrics["candidate_id"] != candidate_id)
            or (metrics.get("action_type") is not None and metrics["action_type"] != action_type)
            or metrics.get("bindings") != ledger["bindings"]
        ):
            return _failure("rejected", "incomplete_metrics_binding_mismatch")
        return row
    if (
        not isinstance(metrics, Mapping)
        or metrics.get("schema_version") != _METRICS_SCHEMA
        or metrics != projected
    ):
        return _failure("rejected", "descriptive_metrics_mismatch")
    for side, probability_key, probability_field, hp_field in (
        ("target", "ko_probability", "target_ko_probability", "target_final_hp_distribution"),
        ("own", "self_faint_probability", "own_faint_probability", "own_final_hp_distribution"),
    ):
        side_metrics = metrics[side]
        if side_metrics["status"] == "resolved":
            fields[probability_field] = _available(side_metrics[probability_key])
            fields[hp_field] = _available(side_metrics["final_hp_distribution"])
        elif side_metrics["status"] == "not_applicable":
            fields[probability_field] = _unavailable("not_applicable")
            fields[hp_field] = _unavailable("not_applicable")
        else:
            fields[probability_field] = _unavailable(side_metrics.get("reason", "metric_incomplete"))
            fields[hp_field] = _unavailable(side_metrics.get("reason", "metric_incomplete"))
    for source_key, field_key, side in (
        ("target_ko", "guaranteed_target_ko", "target"),
        ("self_faint", "guaranteed_self_faint", "own"),
    ):
        if metrics[side]["status"] == "resolved":
            fields[field_key] = _available(metrics["guaranteed_facts"][source_key])
        else:
            fields[field_key] = _unavailable(metrics[side].get("reason", metrics[side]["status"]))
    row["status"] = "complete" if candidate["evidence_class"] != "incomplete" and all(
        metrics[side]["status"] in {"resolved", "not_applicable"} for side in ("target", "own")
    ) else "incomplete"
    return row


def _bound(bindings: Any, provenance: Mapping[str, Any], candidate_id: str, action_type: str) -> bool:
    if not isinstance(bindings, Mapping) or any(bindings.get(key) != value for key, value in provenance.items()):
        return False
    if action_type == "attack":
        target = bindings.get("target")
        return (
            bindings.get("attacker") == provenance["decision_owner"]
            and isinstance(target, Mapping)
            and set(target) == {"session_id", "side", "slot_index", "pokemon_id"}
            and target.get("session_id") == provenance["session_id"]
            and target.get("side") in {"self", "opponent"}
            and target["side"] != provenance["decision_owner"]["side"]
            and isinstance(target.get("slot_index"), int)
            and not isinstance(target["slot_index"], bool)
            and target["slot_index"] >= 0
            and isinstance(target.get("pokemon_id"), str)
            and bool(target["pokemon_id"])
            and isinstance(bindings.get("move_id"), str)
            and candidate_id == f"attack:{bindings['move_id']}"
        )
    return True


def _available(value: Any) -> dict[str, Any]:
    return {"availability": "available", "value": value}


def _unavailable(reason: str) -> dict[str, str]:
    return {"availability": "unavailable", "reason": reason}


def _failure(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason, **extra}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value
