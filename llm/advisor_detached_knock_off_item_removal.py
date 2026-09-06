"""Typed, post-hit Knock Off item consequence; it never mutates runtime D0."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def materialize_detached_knock_off_item_removal(*, authority: Mapping[str, Any], source_leaf: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(authority, Mapping) or authority.get("status") != "resolved":
        return {"status": "incomplete", "reason": "knock_off_item_authority_unavailable"}
    if not isinstance(source_leaf, Mapping) or source_leaf.get("hit_state") not in {"hit", "miss"}:
        return {"status": "rejected", "reason": "knock_off_source_hit_invalid"}
    if authority.get("move_id") != "knock-off" or source_leaf.get("provenance", {}).get("move_id") != "knock-off":
        return {"status": "rejected", "reason": "knock_off_move_binding_mismatch"}
    if source_leaf.get("provenance", {}).get("target") != authority.get("target"):
        return {"status": "rejected", "reason": "knock_off_target_binding_mismatch"}
    before, removable = authority.get("item_before"), authority.get("removable")
    if authority.get("item_state") == "known_absent":
        return {"status": "resolved", "outcome": "not_applicable", "item_before": None, "item_after": None,
                "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"]}
    if not isinstance(before, str) or not isinstance(removable, bool):
        return {"status": "rejected", "reason": "knock_off_item_authority_invalid"}
    if source_leaf["hit_state"] != "hit":
        return {"status": "resolved", "outcome": "not_removed", "reason": "hit_not_successful", "item_before": before,
                "item_after": before, "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"]}
    # Immunity/protection are represented by zero direct damage; a hit leaf alone
    # is not enough to claim a successful applicable Knock Off.
    consequences = source_leaf.get("consequences")
    if not isinstance(consequences, Mapping) or not isinstance(consequences.get("damage"), int) or consequences["damage"] <= 0:
        return {"status": "resolved", "outcome": "not_removed", "reason": "no_applicable_damage", "item_before": before,
                "item_after": before, "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"]}
    source_hit = consequences.get("source_hit_context")
    if not isinstance(source_hit, Mapping) or source_hit.get("target_routing") != "target":
        return {"status": "resolved", "outcome": "not_removed", "reason": "unsupported_or_substitute_target_routing", "item_before": before,
                "item_after": before, "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"]}
    if not removable:
        return {"status": "resolved", "outcome": "not_removed", "reason": "item_not_removable", "item_before": before,
                "item_after": before, "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"]}
    sticky_hold = authority.get("sticky_hold")
    if not isinstance(sticky_hold, bool):
        return {"status": "incomplete", "reason": "sticky_hold_execution_authority_required"}
    target_hp = consequences.get("target_final_hp") if isinstance(consequences, Mapping) else None
    if not isinstance(target_hp, int) or isinstance(target_hp, bool) or target_hp < 0:
        return {"status": "rejected", "reason": "knock_off_target_survival_binding_invalid"}
    if sticky_hold and target_hp > 0:
        return {"status": "resolved", "outcome": "not_removed", "reason": "sticky_hold_target_survived", "item_before": before,
                "item_after": before, "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"]}
    return {"status": "resolved", "outcome": "removed", "item_before": before, "item_after": None,
            "authority": deepcopy(dict(authority)), "source_hit": source_leaf["leaf_id"],
            "provenance": "detached-knock-off-item-removal-v1"}
