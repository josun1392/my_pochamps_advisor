"""Immutable target-stage result for a resolved pure status execution authority."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any, Mapping

from llm.advisor_observed_damage_application import apply_canonical_stage_delta

SCHEMA_VERSION = "detached-pure-status-action-materialization-v1"


def materialize_detached_pure_status_action(*, execution_authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(execution_authority, Mapping): return _result("rejected", "pure_status_execution_authority_invalid", {})
    if execution_authority.get("status") != "resolved": return _result(execution_authority.get("status", "rejected"), execution_authority.get("reason", "pure_status_execution_unavailable"), _base(execution_authority))
    base = _base(execution_authority)
    effect = execution_authority.get("canonical_effect", {}).get("effect") if isinstance(execution_authority.get("canonical_effect"), Mapping) else None
    before = execution_authority.get("current_target_defense_stage")
    if base is None or not isinstance(effect, Mapping) or effect.get("consequence_family") != "target_stage_change" or effect.get("stat") != "defense" or effect.get("delta") != -1 or not isinstance(before, int) or isinstance(before, bool) or not -6 <= before <= 6:
        return _result("rejected", "pure_status_execution_authority_shape_invalid", base or {})
    state = execution_authority.get("accuracy_or_prevention_outcome")
    if state == "prevented": return _leaf(base, "status_action_prevented", before, before, 0, execution_authority)
    if state == "missed": return _leaf(base, "status_action_missed", before, before, 0, execution_authority)
    if state != "ordinary": return _result("rejected", "pure_status_execution_outcome_invalid", base)
    after = apply_canonical_stage_delta(before, -1)
    return _leaf(base, "status_action_applied" if after != before else "status_action_no_effect", before, after, after - before, execution_authority)


def _leaf(base: Mapping[str, Any], outcome: str, before: int, after: int, actual: int, authority: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome,
            "probability": {"numerator": 1, "denominator": 1}, "hit_state": "not_applicable", "critical_state": "not_applicable", "damage_roll": "not_applicable", "damage": "not_applicable",
            "stage_transition": {"target": deepcopy(base["target"]), "stat": "defense", "pre_stage": before, "requested_delta": -1, "actual_delta": actual, "post_stage": after},
            "execution_authority": deepcopy(dict(authority)), "provenance": "strict_detached_pure_status_action_materialization_v1"}


def _base(value: Mapping[str, Any]) -> dict[str, Any] | None:
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "target", "action_id", "move_id")
    if not all(key in value for key in keys) or not all(isinstance(value.get(key), str) and value[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "action_id", "move_id")) or not all(isinstance(value.get(key), Mapping) for key in ("decision_owner", "actor", "target")): return None
    return {key: deepcopy(value[key]) for key in keys}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
