"""Strict current persistent Berry-eaten state authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_berry_eaten_state import resolve_canonical_berry_eaten_lifecycle

SCHEMA_VERSION = "runtime-d0-current-berry-eaten-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def project_current_berry_eaten_authority(
    *, session_id: str, source_runtime_fingerprint: str,
    source_branch_fingerprint: str, owner: Mapping[str, Any],
    state: Any, provenance: Any,
) -> dict[str, Any]:
    base = {
        "schema_version": SCHEMA_VERSION, "session_id": session_id,
        "source_runtime_fingerprint": source_runtime_fingerprint,
        "source_branch_fingerprint": source_branch_fingerprint,
        "owner": deepcopy(dict(owner)) if isinstance(owner, Mapping) else owner,
    }
    if not _owner(owner) or owner.get("session_id") != session_id:
        return {"status": "rejected", **base, "reason": "berry_eaten_owner_invalid"}
    lifecycle = resolve_canonical_berry_eaten_lifecycle()
    if lifecycle.get("status") != "resolved":
        return {"status": "rejected", **base, "reason": lifecycle.get("reason", "berry_eaten_lifecycle_unavailable")}
    if state is None or state == {"knowledge": "unknown"}:
        return {"status": "incomplete", **base, "state": "unknown", "reason": "berry_eaten_state_unknown"}
    if state not in {"known_true", "known_false"} or not _provenance(provenance):
        return {"status": "rejected", **base, "reason": "berry_eaten_runtime_state_invalid"}
    return {
        "status": "resolved", **base, "state": state,
        "value": state == "known_true", "state_provenance": deepcopy(dict(provenance)),
        "lifecycle_authority": lifecycle,
        "provenance": "reducer_persistent_berry_eaten_state_bound_to_runtime_d0_v1",
    }


def freeze_runtime_d0_current_berry_eaten_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any],
) -> dict[str, Any]:
    from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or not _owner(owner):
        return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "invalid_runtime_d0_or_owner"}
    if strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner):
        return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "berry_eaten_active_owner_mismatch"}
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": fresh.get("reason", "stale_runtime_d0")}
    authority = strategy_d0.get("current_berry_eaten_authority", {}).get(owner["side"])
    if not isinstance(authority, Mapping) or authority.get("owner") != dict(owner):
        return {"status": "rejected", "schema_version": SCHEMA_VERSION, "reason": "berry_eaten_d0_authority_missing"}
    return deepcopy(dict(authority))


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"]) and isinstance(value.get("session_id"), str) and bool(value["session_id"])


def _provenance(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == "berry_eaten_state_observed" and value.get("trust") == "user_confirmed_observation" and isinstance(value.get("source_observation_id"), str) and bool(value["source_observation_id"]) and isinstance(value.get("source_sequence"), int) and not isinstance(value.get("source_sequence"), bool) and value["source_sequence"] >= 1
