"""Closed, identity-aware rules shared by atomic item-swap status actions."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_knock_off_item_power_and_removal import resolve_knock_off_target_item


_MOVES = {"trick", "switcheroo"}


def resolve_canonical_atomic_item_swap_status_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Recognize only the two later-consumable atomic-swap status move ids."""
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    if move_id not in _MOVES:
        return {"status": "unsupported", "move_id": move_id, "reason": "move_not_in_atomic_item_swap_status_catalog"}
    expected = {"move_id": move_id, "category": "status", "target": "selected-pokemon"}
    if not isinstance(move, Mapping) or any(move.get(key) != value for key, value in expected.items()):
        return {"status": "rejected", "move_id": move_id, "reason": "atomic_item_swap_status_metadata_mismatch"}
    return {"status": "resolved", "move_id": move_id,
            "effect": {**expected, "family": "atomic_item_swap_status", "contact": False, "damage": "not_applicable"},
            "provenance": "canonical_atomic_item_swap_status_v1"}


def resolve_atomic_item_swap_side_legality(*, holder_item_authority: Mapping[str, Any] | Any,
                                            holder_species: str | None,
                                            incoming_item_authority: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Resolve outgoing transferability and incoming receivability separately.

    The existing Knock Off item/species resolver is the canonical lower-level
    special-item authority.  Its identity-bound exception is deliberately
    reused for both directions rather than duplicating a Mega Stone table.
    """
    outgoing = resolve_knock_off_target_item(item_authority=holder_item_authority, target_species=holder_species)
    incoming = resolve_knock_off_target_item(item_authority=incoming_item_authority, target_species=holder_species)
    if outgoing.get("status") != "resolved" or incoming.get("status") != "resolved":
        return {"status": "incomplete", "outgoing": deepcopy(outgoing), "incoming": deepcopy(incoming),
                "reason": "atomic_item_swap_legality_authority_unknown"}
    holder_state, incoming_state = outgoing["item_state"], incoming["item_state"]
    # No outgoing item and no incoming item each impose no directional
    # restriction.  A present item keeps its exact special-item result.
    transferable = True if holder_state == "known_absent" else outgoing["removable"]
    receivable = True if incoming_state == "known_absent" else not incoming["mega_stone_exception"]
    return {"status": "resolved", "holder_item_state": holder_state,
            "incoming_item_state": incoming_state, "transferable": transferable,
            "allowed_to_receive": receivable, "outgoing_item_authority": deepcopy(outgoing),
            "incoming_item_authority": deepcopy(incoming),
            "provenance": "canonical_atomic_item_swap_status_v1"}
