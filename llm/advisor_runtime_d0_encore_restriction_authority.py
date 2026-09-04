"""Strict current-D0 reader for reducer-owned Encore lifecycle state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-encore-restriction-authority-v1"
_OWNER = {"session_id", "side", "slot_index", "pokemon_id"}


def freeze_runtime_d0_encore_restriction_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, owner)
    if base is None: return _result("rejected", "invalid_runtime_d0_or_encore_owner", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current": return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    rows = state.get("current_encore_restrictions") if isinstance(state, Mapping) else None
    if not isinstance(rows, Mapping): return _result("incomplete", "current_encore_restriction_authority_missing", base)
    row = rows.get(owner["side"])
    if not isinstance(row, Mapping): return _result("incomplete", "current_encore_restriction_observation_missing", base)
    if not _row(row): return _result("rejected", "encore_restriction_lifecycle_invalid", base)
    activation_owner = row["owner"]
    if activation_owner != dict(owner):
        if row["state"] != "not_active" or row["retired_reason"] != "switch_out": return _result("rejected", "encore_restriction_owner_binding_mismatch", base)
        return _resolved(base, owner, row, activation_owner)
    return _resolved(base, owner, row)


def _resolved(base: Mapping[str, Any], owner: Mapping[str, Any], row: Mapping[str, Any], activation_owner: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "owner": deepcopy(dict(owner)), "state": row["state"], "locked_move_id": row["locked_move_id"], "remaining_target_turns": row["remaining_target_turns"], "activation_id": row["activation_id"], "source_action_id": row["source_action_id"], "last_used_execution_id": row["last_used_execution_id"], "retired_reason": row["retired_reason"], "reducer_lifecycle": {"application": deepcopy(dict(row["application_provenance"])), "current": deepcopy(dict(row["lifecycle_provenance"]))}, "provenance": "strict_runtime_d0_current_encore_restriction_v1"}
    if activation_owner is not None: result["retired_activation_owner"] = deepcopy(dict(activation_owner))
    return result


def _row(row: Mapping[str, Any]) -> bool:
    required = {"schema_version", "owner", "restriction", "activation_id", "source_action_id", "source_move_id", "locked_move_id", "last_used_execution_id", "state", "remaining_target_turns", "applied_turn", "last_completed_turn", "retired_reason", "application_provenance", "lifecycle_provenance"}
    if set(row) != required or row.get("schema_version") != "reducer-action-restriction-lifecycle-v1" or row.get("restriction") != "encore" or row.get("source_move_id") != "encore" or row.get("state") not in {"active", "not_active"}: return False
    if not isinstance(row.get("owner"), Mapping) or set(row["owner"]) != _OWNER or not all(isinstance(row.get(key), str) and row[key] for key in ("activation_id", "source_action_id", "locked_move_id", "last_used_execution_id")): return False
    active, remaining = row["state"] == "active", row.get("remaining_target_turns")
    if active != (isinstance(remaining, int) and not isinstance(remaining, bool) and 1 <= remaining <= 3) or active != (row.get("retired_reason") is None): return False
    return all(isinstance(row.get(key), Mapping) and row[key].get("trust") == "user_confirmed_observation" for key in ("application_provenance", "lifecycle_provenance"))


def _base(d0: Any, owner: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(owner, Mapping) or set(owner) != _OWNER or d0.get("active_owners", {}).get(owner.get("side")) != dict(owner): return None
    if not all(isinstance(d0.get(key), str) and d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "owner": deepcopy(dict(owner))}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
