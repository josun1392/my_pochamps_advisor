"""Closed rules for Knock Off's target-item power and removal eligibility."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from advisor.damage.items import get_mega_form, is_mega_stone
from advisor.damage.q12 import Q12_ONE, apply_modifier


_ITEMS_PATH = Path("data/static/champions_legal_items.json")
_KNOCK_OFF_Q12 = 6144


def resolve_canonical_knock_off_move(*, move: Mapping[str, Any] | Any) -> dict[str, Any]:
    move_id = move.get("move_id") if isinstance(move, Mapping) else None
    if move_id != "knock-off":
        return {"status": "unsupported", "move_id": move_id, "reason": "move_not_in_knock_off_catalog"}
    effect = {
        "move_id": "knock-off", "type": "dark", "category": "physical", "base_power": 65,
        "accuracy": 100, "priority": 0, "contact": True, "protection_blockable": True,
        "power_modifier_q12": _KNOCK_OFF_Q12, "family": "target_held_item_power_and_removal",
    }
    if not isinstance(move, Mapping) or any(move.get(key) != value for key, value in effect.items() if key in move):
        return {"status": "rejected", "move_id": move_id, "reason": "catalog_metadata_mismatch"}
    return {"status": "resolved", "move_id": move_id, "effect": effect, "provenance": "canonical-knock-off-item-power-and-removal-v1"}


@lru_cache(maxsize=1)
def _known_item_ids() -> frozenset[str]:
    raw = json.loads(_ITEMS_PATH.read_text(encoding="utf-8"))
    rows = []
    if isinstance(raw, Mapping):
        rows.extend(raw.get("items") if isinstance(raw.get("items"), list) else [])
        rows.extend(raw.get("damage_supported_non_legal_items") if isinstance(raw.get("damage_supported_non_legal_items"), list) else [])
    return frozenset(row["item_id"] for row in rows if isinstance(row, Mapping) and isinstance(row.get("item_id"), str))


def resolve_knock_off_target_item(*, item_authority: Mapping[str, Any] | Any, target_species: str | None) -> dict[str, Any]:
    """Resolve only exact target-held-item eligibility; unknown never means absent."""
    status = item_authority.get("status") if isinstance(item_authority, Mapping) else None
    if status == "known_absent":
        return {"status": "resolved", "item_state": "known_absent", "item_before": None, "removable": False,
                "boost_eligible": False, "item_after_on_success": None, "power_modifier_q12": Q12_ONE,
                "effective_power": 65, "mega_stone_exception": False, "provenance": "canonical-knock-off-item-power-and-removal-v1"}
    item_id = item_authority.get("value") if isinstance(item_authority, Mapping) else None
    if status != "known" or not isinstance(item_id, str) or not item_id:
        return {"status": "incomplete", "item_state": "unknown", "missing_inputs": ["defender.item"]}
    if item_id not in _known_item_ids():
        return {"status": "incomplete", "item_state": "known_present", "item_before": item_id,
                "missing_inputs": ["defender.item_removability"]}
    if is_mega_stone(item_id):
        if not isinstance(target_species, str) or not target_species:
            return {"status": "incomplete", "item_state": "known_present", "item_before": item_id,
                    "missing_inputs": ["defender.species_for_mega_stone_ownership"]}
        exception = get_mega_form(item_id, target_species) is not None
        # A recognized stone held by another exact species is removable.
        removable = not exception
    else:
        exception, removable = False, True
    modifier = _KNOCK_OFF_Q12 if removable else Q12_ONE
    return {"status": "resolved", "item_state": "known_present", "item_before": item_id, "removable": removable,
            "boost_eligible": removable, "item_after_on_success": None if removable else item_id,
            "power_modifier_q12": modifier, "effective_power": apply_modifier(65, modifier),
            "mega_stone_exception": exception, "provenance": "canonical-knock-off-item-power-and-removal-v1"}
