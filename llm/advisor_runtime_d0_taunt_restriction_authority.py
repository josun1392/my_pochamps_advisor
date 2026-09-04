"""Strict current-D0 reader for an explicitly reducer-owned Taunt restriction."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-taunt-restriction-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_taunt_restriction_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    """Read one exact current active's Taunt state; absence is never neutrality.

    The reducer must provide ``state.current_taunt_restrictions[side]``.  It is
    deliberately a current authority, not a predictive mutation and not a
    duration estimate inferred from turn numbers.
    """
    base = _base(strategy_d0, owner)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_taunt_owner", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    rows = state.get("current_taunt_restrictions") if isinstance(state, Mapping) else None
    if not isinstance(rows, Mapping):
        return _result("incomplete", "current_taunt_restriction_authority_missing", base)
    row = rows.get(owner["side"])
    if not isinstance(row, Mapping):
        return _result("incomplete", "current_taunt_restriction_observation_missing", base)
    if row.get("owner") != dict(owner):
        return _result("rejected", "taunt_restriction_owner_binding_mismatch", base)
    state_name = row.get("state")
    if state_name not in {"active", "not_active"}:
        return _result("rejected", "taunt_restriction_state_invalid", base)
    if state_name == "active":
        remaining = row.get("remaining_target_turns")
        if not isinstance(remaining, int) or isinstance(remaining, bool) or not 1 <= remaining <= 3:
            return _result("rejected", "taunt_restriction_duration_invalid", base)
    elif row.get("remaining_target_turns") is not None:
        return _result("rejected", "inactive_taunt_restriction_has_duration", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base,
            "state": state_name, "remaining_target_turns": row.get("remaining_target_turns"),
            "reducer_lifecycle": deepcopy(dict(row.get("provenance", {}))),
            "provenance": "strict_runtime_d0_current_taunt_restriction_v1"}


def _base(d0: Any, owner: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(owner): return None
    if d0.get("active_owners", {}).get(owner.get("side")) != dict(owner): return None
    if not all(isinstance(d0.get(key), str) and d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "owner": deepcopy(dict(owner))}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
