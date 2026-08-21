"""Exact detached Black Sludge tier-five item residual adapter."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _owners, _sync_hp
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item, _types
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def apply_owner_black_sludge_end_of_turn(*, state: dict[str, Any], side: str, owner: Mapping[str, Any], source_branch_fingerprint: str) -> dict[str, Any]:
    """Apply exact Black Sludge recovery or damage to one exact living owner."""
    owners = _owners(state)
    if owners is None or side not in owners or dict(owner) != owners[side] or fingerprint_transition_preview_state(state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_foreign_black_sludge_owner")
    item = _item(state, side)
    if item is _UNKNOWN:
        return _result("incomplete", "black_sludge_current_item_authority")
    if item != "black-sludge":
        return _result("rejected", "black_sludge_item_required")
    current_type = _types(state, side)
    if current_type is None:
        return _result("incomplete", "black_sludge_current_type_authority")
    active = state["active"][side]
    if active["fainted"]:
        return _result("rejected", "black_sludge_fainted_owner")
    hp, maximum = active["current_hp"], active["max_hp"]
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1 or not 0 < hp <= maximum:
        return _result("incomplete", "black_sludge_current_hp_authority")
    poison_type = "poison" in current_type
    amount = maximum // (16 if poison_type else 8)
    post = min(maximum, hp + amount) if poison_type else max(0, hp - amount)
    active["current_hp"], active["fainted"] = post, post == 0
    _sync_hp(state, side, post, maximum)
    return {"status": "resolved", "trace": {"effect": "black_sludge_recovery" if poison_type else "black_sludge_damage", "owner": deepcopy(owners[side]), "item": "black-sludge", "current_type": deepcopy(current_type), "pre_hp": hp, "max_hp": maximum, "recovery" if poison_type else "damage": amount, "post_hp": post, "execution_status": "executed" if post != hp else "prevented", "outcome": "recovered" if poison_type and post != hp else "already_full_hp" if poison_type else "damaged", "guaranteed_ko": post == 0, "provenance": "detached_branch_black_sludge_item_residual_v1"}}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
