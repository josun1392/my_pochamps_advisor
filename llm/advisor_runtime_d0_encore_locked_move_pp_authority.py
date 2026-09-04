"""Narrow current PP-usability authority for Encore's locked opponent move."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-encore-locked-move-pp-authority-v1"


def freeze_runtime_d0_encore_locked_move_pp_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any], move_id: str) -> dict[str, Any]:
    """Use only an exact current reducer usability record; absence is unknown PP."""
    base = _base(strategy_d0, owner, move_id)
    if base is None: return _result("rejected", "invalid_runtime_d0_encore_pp_owner", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current": return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    side = state.get("opponent_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    pokemon = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    records = pokemon.get("current_move_usability") if isinstance(pokemon, Mapping) else None
    row = records.get(move_id) if isinstance(records, Mapping) else None
    if not isinstance(row, Mapping): return _result("incomplete", "encore_locked_move_pp_unobserved", base)
    provenance = row.get("provenance")
    if row.get("status") not in {"known_usable", "known_unusable"} or not isinstance(provenance, Mapping) or provenance.get("source_sequence") != state.get("last_applied_observation_sequence"):
        return _result("incomplete", "encore_locked_move_pp_not_current", base)
    if row["status"] == "known_usable": return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "usable": True, "usability": deepcopy(dict(row)), "provenance": "strict_current_opponent_move_usability_for_encore_v1"}
    if row.get("reason") == "no_pp": return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "usable": False, "usability": deepcopy(dict(row)), "provenance": "strict_current_opponent_move_usability_for_encore_v1"}
    return _result("incomplete", "encore_locked_move_pp_not_isolated_from_other_restriction", base)


def _base(d0: Any, owner: Any, move_id: Any) -> dict[str, Any] | None:
    required = {"session_id", "side", "slot_index", "pokemon_id"}
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(owner, Mapping) or set(owner) != required or owner.get("side") != "opponent" or d0.get("active_owners", {}).get("opponent") != dict(owner) or not isinstance(move_id, str) or not move_id:
        return None
    if not all(isinstance(d0.get(key), str) and d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "owner": deepcopy(dict(owner)), "move_id": move_id}


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
