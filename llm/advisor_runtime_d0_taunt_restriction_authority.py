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
    if not _valid_lifecycle_row(row):
        return _result("rejected", "taunt_restriction_lifecycle_invalid", base)
    activation_owner = row["owner"]
    if activation_owner != dict(owner):
        # The reducer's switch transition is explicit non-transfer evidence:
        # the current active cannot inherit the retired outgoing activation.
        if row.get("state") != "not_active" or row.get("retired_reason") != "switch_out":
            return _result("rejected", "taunt_restriction_owner_binding_mismatch", base)
        return _resolved(base, owner, row, activation_owner=activation_owner)
    state_name = row.get("state")
    if state_name not in {"active", "not_active"}:
        return _result("rejected", "taunt_restriction_state_invalid", base)
    if state_name == "active":
        remaining = row.get("remaining_target_turns")
        if not isinstance(remaining, int) or isinstance(remaining, bool) or not 1 <= remaining <= 3:
            return _result("rejected", "taunt_restriction_duration_invalid", base)
    elif row.get("remaining_target_turns") is not None:
        return _result("rejected", "inactive_taunt_restriction_has_duration", base)
    return _resolved(base, owner, row)


def _resolved(base: Mapping[str, Any], owner: Mapping[str, Any], row: Mapping[str, Any], *, activation_owner: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "owner": deepcopy(dict(owner)),
            "state": row["state"], "remaining_target_turns": row.get("remaining_target_turns"),
            "activation_id": row["activation_id"], "source_action_id": row["source_action_id"],
            "source_move_id": row["source_move_id"], "applied_turn": row["applied_turn"],
            "last_completed_turn": row["last_completed_turn"], "retired_reason": row["retired_reason"],
            "reducer_lifecycle": {"application": deepcopy(dict(row["application_provenance"])), "current": deepcopy(dict(row["lifecycle_provenance"]))},
            "provenance": "strict_runtime_d0_current_taunt_restriction_v1"}
    if activation_owner is not None:
        result["retired_activation_owner"] = deepcopy(dict(activation_owner))
    return result


def _valid_lifecycle_row(row: Mapping[str, Any]) -> bool:
    required = {"schema_version", "owner", "restriction", "activation_id", "source_action_id", "source_move_id", "state", "remaining_target_turns", "applied_turn", "last_completed_turn", "retired_reason", "application_provenance", "lifecycle_provenance"}
    if set(row) != required or row.get("schema_version") != "reducer-action-restriction-lifecycle-v1" or row.get("restriction") != "taunt" or row.get("source_move_id") != "taunt": return False
    if not all(isinstance(row.get(key), str) and bool(row[key]) for key in ("activation_id", "source_action_id", "source_move_id")): return False
    if not isinstance(row.get("applied_turn"), int) or isinstance(row.get("applied_turn"), bool) or row["applied_turn"] < 1: return False
    completed = row.get("last_completed_turn")
    if completed is not None and (not isinstance(completed, int) or isinstance(completed, bool) or completed <= row["applied_turn"]): return False
    for key in ("application_provenance", "lifecycle_provenance"):
        provenance = row.get(key)
        if not isinstance(provenance, Mapping) or provenance.get("trust") != "user_confirmed_observation" or not isinstance(provenance.get("source_observation_id"), str) or not provenance["source_observation_id"] or not isinstance(provenance.get("source_sequence"), int) or isinstance(provenance.get("source_sequence"), bool) or provenance["source_sequence"] < 1: return False
    return True


def _base(d0: Any, owner: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(owner): return None
    if d0.get("active_owners", {}).get(owner.get("side")) != dict(owner): return None
    if not all(isinstance(d0.get(key), str) and d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "owner": deepcopy(dict(owner))}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
