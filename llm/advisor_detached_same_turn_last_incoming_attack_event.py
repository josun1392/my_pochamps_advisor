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
    hit = _last_direct_hit(terminal_leaf, c, strategy_d0, recipient)
    if isinstance(hit, str): return _bad(hit)
    before, after, route, path = hit
    if terminal_leaf.get("action_type") != "attack" or category not in {"physical", "special"} or not isinstance(before, int) or not isinstance(after, int) or before < after or route != "target":
        return _bad("same_turn_incoming_attack_event_not_qualifying")
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, "horizon": "immediate_action_pair", "session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "pair_branch_source_leaf_id": terminal_leaf.get("leaf_id"), "recipient": deepcopy(dict(recipient)), "source_attacker": deepcopy(dict(p["attacker"])), "source_action_id": terminal_leaf.get("candidate_id"), "source_move_id": p.get("move_id"), "source_category": category, "source_hit_state": "hit", "source_hit_path": path, "source_completion_provenance": deepcopy(dict(p)), "target_hp_before": before, "target_hp_after": after, "hp_lost": before-after, "damage_route": route, "qualifying_event": True, "provenance": "exact_branch_local_same_turn_last_incoming_attack_event_v1"}

def _last_direct_hit(leaf: Mapping[str, Any], consequences: Mapping[str, Any], strategy_d0: Mapping[str, Any], recipient: Mapping[str, Any]) -> tuple[int, int, str, dict[str, Any]] | str:
    if leaf.get("hit_state") != "hit": return "incoming_attack_did_not_hit"
    ordered = leaf.get("ordered_hits")
    if isinstance(ordered, (tuple, list)):
        rows = [row for row in ordered if isinstance(row, Mapping) and row.get("target_routing", "target") == "target" and isinstance(row.get("pre_hp"), int) and isinstance(row.get("post_hp"), int)]
        if not rows: return "incoming_attack_last_direct_strike_unproven"
        row = rows[-1]
        return row["pre_hp"], row["post_hp"], row.get("target_routing"), {"leaf_id": leaf.get("leaf_id"), "hit_index": row.get("hit_index"), "critical_state": row.get("critical_state"), "roll_index": row.get("roll_index")}
    source = consequences.get("source_hit_context")
    if not isinstance(source, Mapping): return "incoming_attack_direct_hit_context_missing"
    route = source.get("target_routing", source.get("damage_route")); before, after = source.get("target_pre_hp"), source.get("target_post_hp")
    if source.get("successful_damaging_hit") is False: return "incoming_attack_direct_hit_hp_context_missing"
    if not isinstance(before, int) or not isinstance(after, int):
        before = strategy_d0.get("strategy_state", {}).get("active", {}).get(recipient.get("side"), {}).get("current_hp")
        after = consequences.get("target_final_hp")
    if not isinstance(before, int) or not isinstance(after, int): return "incoming_attack_direct_hit_hp_context_missing"
    return before, after, route, {"leaf_id": leaf.get("leaf_id"), "hit_index": source.get("hit_index"), "critical_state": source.get("critical_state"), "roll_index": source.get("roll_index")}

def _category(leaf: Mapping[str, Any]) -> str | None:
    c = leaf.get("consequences", {})
    interval = c.get("interval") if isinstance(c, Mapping) else None
    move = interval.get("move_metadata") if isinstance(interval, Mapping) else None
    return move.get("category") if isinstance(move, Mapping) else leaf.get("provenance", {}).get("move_category") if isinstance(leaf.get("provenance"), Mapping) else None

def _bad(reason: str) -> dict[str, Any]: return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": reason}
