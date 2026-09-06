"""Strict D0 reader for a reducer-owned same-active previous action result."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_previous_action_failure_power_family import qualifies_as_previous_move_failure
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-previous-action-result-authority-v1"
_OWNER = {"session_id", "side", "slot_index", "pokemon_id"}

def freeze_runtime_d0_previous_action_result_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, owner)
    if base is None: return _result("rejected", "invalid_runtime_d0_or_previous_action_owner", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current": return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None; side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None; pokemon = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    if not isinstance(pokemon, Mapping) or pokemon.get("pokemon_id") != owner["pokemon_id"]: return _result("rejected", "runtime_previous_action_owner_identity_mismatch", base)
    row = pokemon.get("previous_action_result")
    if row is None: return _result("incomplete", "previous_action_result_history_missing", base)
    required = {"schema_version", "owner", "previous_action_id", "selected_move_id", "execution_move_id", "result_class", "source_turn", "provenance"}
    if not isinstance(row, Mapping) or set(row) != required or row.get("schema_version") != "reducer-previous-action-result-v1" or row.get("owner") != dict(owner) or not all(isinstance(row.get(k), str) and row[k] for k in ("previous_action_id", "selected_move_id", "execution_move_id", "result_class")) or not isinstance(row.get("source_turn"), int) or isinstance(row.get("source_turn"), bool) or row["source_turn"] < 1: return _result("rejected", "previous_action_result_history_invalid", base)
    qualified = qualifies_as_previous_move_failure(row["result_class"])
    if qualified is None: return _result("incomplete", "previous_action_result_class_unsupported", base)
    provenance = row.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("trust") != "user_confirmed_observation" or not isinstance(provenance.get("source_sequence"), int): return _result("rejected", "previous_action_result_provenance_invalid", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "previous_action_id": row["previous_action_id"], "selected_move_id": row["selected_move_id"], "execution_move_id": row["execution_move_id"], "previous_action_result_class": row["result_class"], "qualifies_as_previous_move_failure": qualified, "source_turn": row["source_turn"], "source_lifecycle_provenance": deepcopy(dict(provenance)), "provenance": "strict_runtime_d0_reducer_previous_action_result_v1"}

def _base(d0: Any, owner: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(owner, Mapping) or set(owner) != _OWNER or d0.get("active_owners", {}).get(owner.get("side")) != dict(owner): return None
    if not all(isinstance(d0.get(k), str) and d0[k] for k in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "owner": deepcopy(dict(owner))}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
