"""Immutable, branch-local evidence consumed by Counter and Mirror Coat."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "detached-same-turn-last-incoming-attack-event-v1"

def materialize_detached_same_turn_last_incoming_attack_event(*, strategy_d0: Mapping[str, Any], terminal_leaf: Mapping[str, Any], recipient: Mapping[str, Any], source_move_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(strategy_d0, Mapping) or not isinstance(terminal_leaf, Mapping) or not isinstance(recipient, Mapping): return _bad("invalid_same_turn_incoming_event_request")
    p, c = terminal_leaf.get("provenance"), terminal_leaf.get("consequences")
    if not isinstance(p, Mapping) or not isinstance(c, Mapping) or p.get("target") != recipient: return _bad("incoming_event_recipient_binding_mismatch")
    category = source_move_metadata.get("category") if isinstance(source_move_metadata, Mapping) else _category(terminal_leaf)
    before = strategy_d0.get("strategy_state", {}).get("active", {}).get(recipient.get("side"), {}).get("current_hp")
    after = c.get("target_final_hp")
    route = c.get("source_hit_context", {}).get("damage_route", "target") if isinstance(c.get("source_hit_context"), Mapping) else "target"
    if category not in {"physical", "special"} or not isinstance(before, int) or not isinstance(after, int) or before < after or route != "target":
        return _bad("same_turn_incoming_attack_event_not_qualifying")
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "recipient": deepcopy(dict(recipient)), "source_attacker": deepcopy(dict(p["attacker"])), "source_action_id": terminal_leaf.get("candidate_id"), "source_move_id": p.get("move_id"), "source_category": category, "source_hit_state": terminal_leaf.get("hit_state"), "source_completion_provenance": deepcopy(dict(p)), "target_hp_before": before, "target_hp_after": after, "hp_lost": before-after, "damage_route": route, "qualifying_event": terminal_leaf.get("hit_state") == "hit", "provenance": "exact_branch_local_same_turn_last_incoming_attack_event_v1"}

def _category(leaf: Mapping[str, Any]) -> str | None:
    c = leaf.get("consequences", {})
    interval = c.get("interval") if isinstance(c, Mapping) else None
    move = interval.get("move_metadata") if isinstance(interval, Mapping) else None
    return move.get("category") if isinstance(move, Mapping) else leaf.get("provenance", {}).get("move_category") if isinstance(leaf.get("provenance"), Mapping) else None

def _bad(reason: str) -> dict[str, Any]: return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": reason}
