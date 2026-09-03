"""Read-only D0 adapter for the reducer-owned Supreme Overlord entry snapshot."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-supreme-overlord-entry-authority-v1"


def freeze_runtime_d0_supreme_overlord_entry_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or owner != strategy_d0.get("active_owners", {}).get(owner.get("side") if isinstance(owner, Mapping) else None):
        return _result("rejected", "supreme_overlord_owner_not_current_active", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current": return _result("rejected", fresh.get("reason", "stale_runtime_d0"), _base(strategy_d0, owner))
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    rows = state.get("supreme_overlord_entry_snapshots") if isinstance(state, Mapping) else None
    base = _base(strategy_d0, owner)
    if not isinstance(rows, list): return _result("incomplete", "supreme_overlord_entry_snapshot_missing", base)
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("owner") == owner and row.get("active") is True]
    if len(matches) != 1: return _result("incomplete", "supreme_overlord_current_entry_snapshot_unavailable", base)
    row = matches[0]
    if row.get("schema_version") != "supreme-overlord-entry-snapshot-v1" or row.get("session_id") != strategy_d0["session_id"] or row.get("status") != "resolved" or row.get("fallen_allies_count") != min(row.get("raw_allied_faint_count", -1), 5):
        return _result("rejected", "supreme_overlord_entry_snapshot_invalid", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "entry_snapshot": deepcopy(dict(row)), "provenance": "reducer_owned_frozen_entry_snapshot_v1"}


def _base(d0: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    return {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(d0.get("decision_owner")), "owner": deepcopy(dict(owner))}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
