"""Move-bound Supreme Overlord applicability from a frozen entry snapshot."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_supreme_overlord_entry_authority import (
    SCHEMA_VERSION as ENTRY_AUTHORITY_SCHEMA_VERSION,
    freeze_runtime_d0_supreme_overlord_entry_authority,
)


SCHEMA_VERSION = "runtime-d0-supreme-overlord-damage-authority-v1"
_MODIFIERS = (4096, 4506, 4915, 5325, 5734, 6144)


def freeze_runtime_d0_supreme_overlord_damage_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, attacker, target, move_metadata)
    if base is None: return _result("rejected", "supreme_overlord_damage_identity_invalid", {})
    entry = freeze_runtime_d0_supreme_overlord_entry_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=attacker)
    if entry.get("status") != "resolved": return _result(entry.get("status", "rejected"), entry.get("reason", "supreme_overlord_entry_snapshot_unavailable"), base, entry_authority=entry)
    snapshot = entry.get("entry_snapshot")
    ability = _ability(runtime_snapshot, attacker)
    if ability != "supreme-overlord": return _result("incomplete", "supreme_overlord_attacker_ability_unknown_or_changed", base, entry_authority=entry)
    fallen = snapshot.get("fallen_allies_count") if isinstance(snapshot, Mapping) else None
    raw = snapshot.get("raw_allied_faint_count") if isinstance(snapshot, Mapping) else None
    if not isinstance(fallen, int) or isinstance(fallen, bool) or not 0 <= fallen <= 5 or not isinstance(raw, int) or isinstance(raw, bool) or raw < fallen or fallen != min(raw, 5):
        return _result("rejected", "supreme_overlord_entry_count_invalid", base, entry_authority=entry)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "attacker_ability": ability, "entry_authority": deepcopy(entry), "entry_token": snapshot["entry_token"], "raw_allied_faint_count": raw, "fallen_allies_count": fallen, "modifier_q12": _MODIFIERS[fallen], "outcome": "applicable" if fallen else "known_neutral", "provenance": "frozen_reducer_entry_snapshot_to_native_bp_modifier_v1"}


def valid_runtime_d0_supreme_overlord_damage_authority(value: Any, *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move_id: str) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION or value.get("status") != "resolved": return False
    expected = {"session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "decision_owner": strategy_d0.get("decision_owner"), "attacker": attacker, "target": target, "move_id": move_id, "attacker_ability": "supreme-overlord"}
    if any(value.get(key) != item for key, item in expected.items()): return False
    fallen, raw = value.get("fallen_allies_count"), value.get("raw_allied_faint_count")
    entry = value.get("entry_authority")
    if not isinstance(fallen, int) or isinstance(fallen, bool) or not 0 <= fallen <= 5 or not isinstance(raw, int) or isinstance(raw, bool) or raw < fallen or fallen != min(raw, 5) or value.get("modifier_q12") != _MODIFIERS[fallen] or value.get("outcome") != ("applicable" if fallen else "known_neutral"):
        return False
    snapshot = entry.get("entry_snapshot") if isinstance(entry, Mapping) else None
    entry_expected = {
        "schema_version": ENTRY_AUTHORITY_SCHEMA_VERSION,
        "status": "resolved",
        "session_id": strategy_d0.get("session_id"),
        "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"),
        "decision_owner": strategy_d0.get("decision_owner"),
        "owner": attacker,
    }
    return (
        isinstance(entry, Mapping)
        and all(entry.get(key) == item for key, item in entry_expected.items())
        and isinstance(snapshot, Mapping)
        and snapshot.get("owner") == attacker
        and snapshot.get("active") is True
        and snapshot.get("entry_token") == value.get("entry_token")
        and snapshot.get("fallen_allies_count") == fallen
        and snapshot.get("raw_allied_faint_count") == raw
    )


def _base(d0: Any, attacker: Any, target: Any, move: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or attacker != d0.get("decision_owner") or target != d0.get("active_owners", {}).get("opponent") or not isinstance(move, Mapping) or not isinstance(move.get("move_id"), str): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": move["move_id"]}


def _ability(snapshot: Any, attacker: Mapping[str, Any]) -> str | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None; side = state.get("self_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; row = roster.get(attacker.get("slot_index")) if isinstance(roster, Mapping) else None
    return row.get("current_ability") if isinstance(row, Mapping) and isinstance(row.get("current_ability"), str) else None


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
