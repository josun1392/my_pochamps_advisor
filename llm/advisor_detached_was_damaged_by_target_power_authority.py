"""Detached, pair-local power evidence for Avalanche and Revenge.

This consumes an already-materialized preceding action leaf.  It is neither
persistent turn state nor the Counter/Mirror Coat last-hit adapter: every
direct strike in a source multi-hit leaf is considered because this predicate
is existential.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_was_damaged_power_family import resolve_canonical_was_damaged_power_move


SCHEMA_VERSION = "detached-was-damaged-by-target-power-authority-v2"


def materialize_detached_was_damaged_by_target_power_authority(
    *, strategy_d0: Mapping[str, Any], move: Mapping[str, Any],
    user: Mapping[str, Any], target: Mapping[str, Any],
    incoming_event: Mapping[str, Any] | None,
    source_terminal_leaf: Mapping[str, Any] | None = None,
    execution_order_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    canonical = resolve_canonical_was_damaged_power_move(move=move)
    if canonical.get("status") != "resolved":
        return _bad(canonical.get("status", "rejected"), canonical.get("reason", "catalog_unavailable"))
    bindings = _bindings(strategy_d0=strategy_d0, move=move, user=user, target=target)
    if isinstance(bindings, str):
        return _bad("rejected", bindings)
    if source_terminal_leaf is None:
        return _resolved(canonical, bindings, False, None, None, execution_order_provenance)
    source = _validate_source_leaf(source_terminal_leaf, bindings)
    if isinstance(source, str):
        return _bad("rejected", source)
    event = _validate_event(incoming_event, bindings, source_terminal_leaf)
    if isinstance(event, str):
        return _bad("rejected", event)
    hit_evidence = _positive_direct_hits(source_terminal_leaf)
    if isinstance(hit_evidence, str):
        if hit_evidence == "known_non_damaging_source_leaf":
            return _resolved(canonical, bindings, False, None, event, execution_order_provenance)
        return _bad("incomplete", hit_evidence)
    if hit_evidence:
        return _resolved(canonical, bindings, True, hit_evidence[0], event, execution_order_provenance)
    # Single-hit ordinary and special-damage leaves use source_hit_context
    # rather than ordered_hits.  The canonical event is then the exact
    # positive underlying-HP proof; it is not a Counter-style damage input.
    if isinstance(event, Mapping) and event.get("status") == "resolved" and event.get("hp_lost", 0) > 0:
        path = event.get("source_hit_path")
        hit = {"leaf_id": source_terminal_leaf["leaf_id"], "hit_index": path.get("hit_index") if isinstance(path, Mapping) else None, "actual_hp_loss": event["hp_lost"], "target_routing": "target"}
        return _resolved(canonical, bindings, True, hit, event, execution_order_provenance)
    if isinstance(event, Mapping) and event.get("status") == "resolved" and event.get("hp_lost") == 0:
        return _resolved(canonical, bindings, False, None, event, execution_order_provenance)
    if source_terminal_leaf.get("hit_state") in {"miss", "blocked", "immune", "failure"}:
        return _resolved(canonical, bindings, False, None, event, execution_order_provenance)
    return _bad("incomplete", "prior_direct_damage_outcome_unproven")


def _bindings(*, strategy_d0: Mapping[str, Any], move: Mapping[str, Any], user: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any] | str:
    if not all(isinstance(value, Mapping) for value in (strategy_d0, move, user, target)):
        return "was_damaged_power_request_invalid"
    required = ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")
    if any(not isinstance(strategy_d0.get(key), str) or not strategy_d0.get(key) for key in required):
        return "was_damaged_power_d0_provenance_missing"
    active = strategy_d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(user.get("side")) != user or active.get(target.get("side")) != target or user == target:
        return "was_damaged_power_active_identity_mismatch"
    return {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "user": deepcopy(dict(user)), "target": deepcopy(dict(target)), "move_id": move.get("move_id")}


def _validate_source_leaf(leaf: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any] | str:
    provenance = leaf.get("provenance")
    if not isinstance(provenance, Mapping) or leaf.get("action_type") != "attack":
        return "was_damaged_power_source_leaf_invalid"
    if provenance.get("attacker") != bindings["target"] or provenance.get("target") != bindings["user"]:
        return "was_damaged_power_source_identity_mismatch"
    if not isinstance(leaf.get("leaf_id"), str) or not leaf["leaf_id"]:
        return "was_damaged_power_source_leaf_id_missing"
    return deepcopy(dict(provenance))


def _validate_event(event: Mapping[str, Any] | None, bindings: Mapping[str, Any], leaf: Mapping[str, Any]) -> Mapping[str, Any] | None | str:
    if event is None:
        return None
    if not isinstance(event, Mapping):
        return "was_damaged_power_event_invalid"
    if event.get("status") != "resolved":
        return deepcopy(dict(event))
    required = {"session_id": bindings["session_id"], "source_runtime_fingerprint": bindings["source_runtime_fingerprint"], "source_branch_fingerprint": bindings["source_branch_fingerprint"], "pair_branch_source_leaf_id": leaf["leaf_id"], "recipient": bindings["user"], "source_attacker": bindings["target"], "qualifying_event": True, "damage_route": "target"}
    if any(event.get(key) != value for key, value in required.items()):
        return "was_damaged_power_event_provenance_mismatch"
    if not isinstance(event.get("hp_lost"), int) or event["hp_lost"] < 0:
        return "was_damaged_power_event_hp_loss_invalid"
    return deepcopy(dict(event))


def _positive_direct_hits(leaf: Mapping[str, Any]) -> list[dict[str, Any]] | str:
    if leaf.get("hit_state") != "hit":
        return "known_non_damaging_source_leaf"
    hits = leaf.get("ordered_hits")
    if not isinstance(hits, (tuple, list)):
        return []
    evidence: list[dict[str, Any]] = []
    for index, hit in enumerate(hits):
        if not isinstance(hit, Mapping):
            return "was_damaged_power_ordered_hit_invalid"
        if hit.get("target_routing", "target") != "target":
            continue
        pre, post, damage = hit.get("pre_hp"), hit.get("post_hp"), hit.get("actual_damage")
        if isinstance(pre, int) and isinstance(post, int) and pre >= post:
            loss = pre - post
        elif isinstance(damage, int) and damage >= 0:
            loss = damage
        else:
            return "was_damaged_power_direct_hit_hp_loss_unproven"
        if loss > 0:
            evidence.append({"leaf_id": leaf["leaf_id"], "hit_index": hit.get("hit_index", index + 1), "actual_hp_loss": loss, "target_routing": "target"})
    return evidence


def _resolved(canonical: Mapping[str, Any], bindings: Mapping[str, Any], was_damaged: bool, hit: Mapping[str, Any] | None, event: Mapping[str, Any] | None, order: Mapping[str, Any] | None) -> dict[str, Any]:
    effect = canonical["effect"]
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(bindings)), "canonical_base_power": effect["power"], "was_damaged_by_target_before_execution": was_damaged, "selected_base_power": effect["boosted_power"] if was_damaged else effect["power"], "qualifying_hit_provenance": deepcopy(dict(hit)) if isinstance(hit, Mapping) else None, "source_event": deepcopy(dict(event)) if isinstance(event, Mapping) else None, "execution_order_provenance": deepcopy(dict(order)) if isinstance(order, Mapping) else None, "rule": deepcopy(dict(effect)), "provenance": "exact_d0_pair_branch_was_damaged_by_target_before_execution_v2"}


def _bad(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
