"""D0-bound authority for a catalogued direct self-heal execution."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_direct_heal_move_family import resolve_canonical_direct_heal_move
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-direct-heal-execution-authority-v1"


def freeze_runtime_d0_direct_heal_execution_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], path_hp_authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor)
    if base is None: return _result("rejected", "direct_heal_identity_or_d0_invalid", {})
    if path_hp_authority is None:
        fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
        if fresh.get("status") != "current": return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
        hp = strategy_d0.get("strategy_state", {}).get("active", {}).get(actor.get("side"))
        source = "runtime_strategy_d0"
    else:
        hp = path_hp_authority
        source = "detached_path_local"
    current, maximum, fainted = (hp or {}).get("current_hp"), (hp or {}).get("max_hp"), (hp or {}).get("fainted")
    if not _hp(current, maximum, fainted): return _result("incomplete", "direct_heal_current_hp_authority_unknown", base)
    canonical = resolve_canonical_direct_heal_move(move=_metadata(action))
    if canonical.get("status") != "resolved": return _result(canonical.get("status", "rejected"), canonical.get("reason", "direct_heal_catalog_unavailable"), base, canonical_effect=canonical)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "canonical_effect": deepcopy(canonical),
            "current_hp": current, "max_hp": maximum, "fainted": fainted, "hp_source": source,
            "provenance": "strict_runtime_d0_direct_heal_execution_freeze_v1"}


def _base(d0: Any, action: Any, actor: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(actor, Mapping): return None
    if d0.get("active_owners", {}).get(actor.get("side")) != dict(actor): return None
    move_id = action.get("identity") or action.get("move_id")
    if action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str) or not isinstance(move_id, str): return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "action_id": action["action_id"], "move_id": move_id}


def _metadata(action: Mapping[str, Any]) -> Mapping[str, Any]:
    value = action.get("move_metadata_authority") or action.get("metadata_authority")
    return value.get("metadata", {}) if isinstance(value, Mapping) and value.get("status") == "resolved" and isinstance(value.get("metadata"), Mapping) else {}


def _hp(current: Any, maximum: Any, fainted: Any) -> bool:
    return isinstance(current, int) and not isinstance(current, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 and 0 <= current <= maximum and fainted is (current == 0)


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
