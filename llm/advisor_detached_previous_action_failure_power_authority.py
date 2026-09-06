"""Bind reducer-owned prior-action evidence to this Stomping Tantrum action."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_previous_action_failure_power_family import resolve_canonical_previous_action_failure_power_move

SCHEMA_VERSION = "runtime-d0-previous-action-result-authority-v1"
def materialize_previous_action_failure_power_authority(*, strategy_d0: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], previous_action_authority: Mapping[str, Any]) -> dict[str, Any]:
    canonical = resolve_canonical_previous_action_failure_power_move(move=move)
    if canonical.get("status") != "resolved": return {"status": canonical.get("status", "rejected"), "schema_version": SCHEMA_VERSION, "reason": canonical.get("reason")}
    if not isinstance(previous_action_authority, Mapping) or previous_action_authority.get("status") != "resolved": return {"status": previous_action_authority.get("status", "incomplete") if isinstance(previous_action_authority, Mapping) else "incomplete", "schema_version": SCHEMA_VERSION, "reason": previous_action_authority.get("reason", "previous_action_result_authority_missing") if isinstance(previous_action_authority, Mapping) else "previous_action_result_authority_missing"}
    expected = {"session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "decision_owner": strategy_d0.get("decision_owner"), "owner": user}
    if any(previous_action_authority.get(k) != v for k, v in expected.items()) or not isinstance(previous_action_authority.get("qualifies_as_previous_move_failure"), bool): return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "previous_action_result_authority_binding_mismatch"}
    effect, condition = canonical["effect"], previous_action_authority["qualifies_as_previous_move_failure"]
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **{k: deepcopy(previous_action_authority[k]) for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "owner", "previous_action_id", "selected_move_id", "execution_move_id", "previous_action_result_class", "source_turn", "source_lifecycle_provenance")}, "move_id": "stomping-tantrum", "trigger_family": "previous_move_failed", "canonical_base_power": effect["power"], "qualifies_as_previous_move_failure": condition, "selected_base_power": effect["boosted_power"] if condition else effect["power"], "rule": deepcopy(effect), "provenance": "strict_runtime_d0_same_active_previous_action_failure_v1"}
