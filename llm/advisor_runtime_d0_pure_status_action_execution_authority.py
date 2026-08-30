"""D0-bound authority for one catalogued pure status action and target."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_pure_status_action_effect import resolve_canonical_pure_status_action_effect
from llm.advisor_runtime_strategy_d0 import freeze_runtime_current_stage_authority, runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-pure-status-action-execution-authority-v1"
_STATUSES = {"incomplete", "unsupported", "rejected"}


def freeze_runtime_d0_pure_status_action_execution_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], prevention_authority: Mapping[str, Any] | None = None, status_accuracy_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None:
        return _result("rejected", "pure_status_action_identity_or_d0_invalid", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    metadata = _metadata(action)
    canonical = resolve_canonical_pure_status_action_effect(move=metadata)
    if canonical.get("status") != "resolved":
        return _result(_status(canonical), canonical.get("reason", "canonical_pure_status_effect_unavailable"), base, canonical_effect=canonical)
    stages = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    if stages.get("status") != "resolved":
        return _result(_status(stages), stages.get("reason", "target_stage_authority_unavailable"), base, canonical_effect=canonical)
    defense = stages.get("stages", {}).get("defense") if isinstance(stages.get("stages"), Mapping) else None
    if not isinstance(defense, Mapping) or defense.get("status") != "known":
        return _result("incomplete", "target_defense_stage_unknown", base, canonical_effect=canonical, current_target_stage_authority=stages)
    if prevention_authority is not None:
        prevention = _prevention(prevention_authority, base)
        if isinstance(prevention, Mapping):
            return _result(_status(prevention), prevention.get("reason", "status_prevention_authority_invalid"), base, canonical_effect=canonical)
        outcome = "prevented" if prevention else None
    else:
        outcome = None
    if outcome is None:
        accuracy = _accuracy(status_accuracy_authority, base)
        if isinstance(accuracy, Mapping):
            return _result(_status(accuracy), accuracy.get("reason", "status_accuracy_authority_required"), base, canonical_effect=canonical)
        outcome = accuracy
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base,
            "canonical_effect": deepcopy(canonical), "current_target_stage_authority": deepcopy(stages),
            "current_target_defense_stage": defense["value"], "accuracy_or_prevention_outcome": outcome,
            "status_accuracy_authority": deepcopy(status_accuracy_authority),
            "prevention_authority": deepcopy(prevention_authority),
            "provenance": "strict_runtime_d0_pure_status_action_execution_freeze_v1"}


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(actor, Mapping) or not isinstance(target, Mapping): return None
    active = d0.get("active_owners", {})
    if active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target) or actor == target or actor.get("side") == target.get("side"): return None
    move_id = action.get("identity")
    if action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str) or not isinstance(move_id, str): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action["action_id"], "move_id": move_id}


def _metadata(action: Mapping[str, Any]) -> Mapping[str, Any]:
    value = action.get("move_metadata_authority") or action.get("metadata_authority")
    if isinstance(value, Mapping) and value.get("status") == "resolved" and isinstance(value.get("metadata"), Mapping): return value["metadata"]
    return {}


def _accuracy(value: Any, base: Mapping[str, Any]) -> str | dict[str, Any]:
    if not isinstance(value, Mapping): return {"status": "incomplete", "reason": "status_accuracy_authority_required"}
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "actor", "target", "action_id", "move_id"):
        if value.get(key) != base.get(key): return {"status": "rejected", "reason": "status_accuracy_authority_binding_mismatch"}
    if value.get("status") != "resolved": return {"status": _status(value), "reason": value.get("reason", "status_accuracy_authority_unavailable")}
    return "missed" if value.get("outcome") == "missed" else "ordinary" if value.get("outcome") == "hit" else {"status": "rejected", "reason": "status_accuracy_outcome_invalid"}


def _prevention(value: Any, base: Mapping[str, Any]) -> bool | dict[str, Any]:
    if value.get("schema_version") == "runtime-d0-crafty-shield-pure-status-applicability-authority-v1":
        mapped = {**value, "schema_version": "crafty-shield-prevention-adapter-v1", "actor": value.get("incoming_actor"), "target": value.get("selected_target"), "action_id": value.get("incoming_action_id"), "move_id": value.get("incoming_move_id")}
        return _prevention(mapped, base)
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "actor", "target", "action_id", "move_id"):
        if value.get(key) != base.get(key): return {"status": "rejected", "reason": "status_prevention_authority_binding_mismatch"}
    if value.get("status") != "resolved": return {"status": _status(value), "reason": value.get("reason", "status_prevention_authority_unavailable")}
    if value.get("outcome") == "prevented": return True
    if value.get("outcome") == "not_applicable": return False
    return {"status": "rejected", "reason": "status_prevention_outcome_invalid"}


def _status(value: Mapping[str, Any]) -> str: return value.get("status") if value.get("status") in _STATUSES else "rejected"
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
