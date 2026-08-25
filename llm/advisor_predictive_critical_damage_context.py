"""Detached paired native damage contexts for a single D0-bound action."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_predictive_normal_formula_interval import build_predictive_normal_formula_interval


SCHEMA_VERSION = "strict-predictive-critical-damage-context-v1"


def materialize_predictive_critical_damage_contexts(
    *,
    branch_state: Mapping[str, Any],
    decision_owner: Mapping[str, Any],
    target_owner: Mapping[str, Any],
    snapshot_damage_input: Mapping[str, Any],
    stat_provenance: Mapping[str, Any],
    trusted_level: int | None,
    source_runtime_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Build exact non-critical and critical intervals from one frozen input.

    This adapter owns no probability or branch semantics.  It only requires
    positive stage evidence and asks the existing native damage path to apply
    the canonical stage selection forward for each criticality.
    """
    non_critical = build_predictive_normal_formula_interval(
        branch_state=branch_state, decision_owner=decision_owner, target_owner=target_owner,
        snapshot_damage_input=snapshot_damage_input, stat_provenance=stat_provenance,
        trusted_level=trusted_level, is_critical=False, source_runtime_fingerprint=source_runtime_fingerprint,
    )
    unavailable = _unavailable(non_critical)
    if unavailable is not None:
        return unavailable
    if not _explicit_stage_evidence(non_critical, is_critical=False):
        return _result("incomplete", "critical_damage_stage_authority_unknown")

    critical = build_predictive_normal_formula_interval(
        branch_state=branch_state, decision_owner=decision_owner, target_owner=target_owner,
        snapshot_damage_input=snapshot_damage_input, stat_provenance=stat_provenance,
        trusted_level=trusted_level, is_critical=True, source_runtime_fingerprint=source_runtime_fingerprint,
    )
    unavailable = _unavailable(critical)
    if unavailable is not None:
        return unavailable
    if not _same_frozen_action(non_critical, critical) or not _explicit_stage_evidence(critical, is_critical=True):
        return _result("rejected", "critical_damage_context_binding_mismatch")

    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "session_id": non_critical["session_id"],
        "source_branch_fingerprint": non_critical["source_branch_fingerprint"],
        "decision_owner": deepcopy(dict(non_critical["decision_owner"])),
        "attacker": deepcopy(dict(non_critical["attacker"])),
        "target": deepcopy(dict(non_critical["target"])),
        "move_id": non_critical["move_id"],
        "non_critical_context": deepcopy(dict(non_critical)),
        "critical_context": deepcopy(dict(critical)),
        "provenance": "same_frozen_d0_native_inputs_to_paired_critical_damage_contexts_v1",
    }


def _unavailable(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return _result("rejected", "invalid_native_damage_context")
    if value.get("status") != "resolved":
        return _result(value.get("status") if value.get("status") in {"incomplete", "unsupported", "rejected"} else "rejected", _reason(value))
    completeness = value.get("completeness")
    if completeness == "exact_complete":
        return None
    return _result("unsupported" if completeness == "unsupported" else "incomplete", _reason(value))


def _explicit_stage_evidence(value: Mapping[str, Any], *, is_critical: bool) -> bool:
    native = value.get("native_evaluator_result")
    evidence = native.get("stat_stage_evidence") if isinstance(native, Mapping) else None
    if not isinstance(evidence, Mapping):
        return False
    raw_keys = ("offensive_stage_stat", "offensive_stage_value", "defensive_stage_stat", "defensive_stage_value")
    if not all(key in evidence for key in raw_keys):
        return False
    if not all(isinstance(evidence[key], int) and not isinstance(evidence[key], bool) for key in ("offensive_stage_value", "defensive_stage_value")):
        return False
    if not is_critical:
        return value.get("scope", {}).get("critical") == "non_critical_assumed"
    return (
        value.get("scope", {}).get("critical") == "critical_assumed"
        and evidence.get("critical_damage_stage_selection") is True
        and all(isinstance(evidence.get(key), int) and not isinstance(evidence.get(key), bool) for key in ("effective_offensive_stage_value", "effective_defensive_stage_value"))
    )


def _same_frozen_action(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in (
        "session_id", "source_branch_fingerprint", "decision_owner", "attacker", "target", "move_id",
    ))


def _reason(value: Mapping[str, Any]) -> str:
    reason = value.get("reason")
    return reason if isinstance(reason, str) and reason else "native_critical_damage_context_unavailable"


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
