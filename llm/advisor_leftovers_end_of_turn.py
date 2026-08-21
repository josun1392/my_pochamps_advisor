"""Exact detached Leftovers recovery adapter."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _owners, _sync_hp
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def apply_owner_leftovers_end_of_turn(*, state: dict[str, Any], side: str, owner: Mapping[str, Any], source_branch_fingerprint: str) -> dict[str, Any]:
    """Apply the canonical item residual to one exact living active holder."""
    owners = _owners(state)
    if owners is None or side not in owners or dict(owner) != owners[side] or fingerprint_transition_preview_state(state) != source_branch_fingerprint:
        return _result("rejected", "stale_or_foreign_leftovers_owner")
    item = _item(state, side)
    if item is _UNKNOWN:
        return _result("incomplete", "leftovers_current_item_authority")
    if item != "leftovers":
        return _result("rejected", "leftovers_item_required")
    active = state["active"][side]
    if active["fainted"]:
        return _result("rejected", "leftovers_fainted_owner")
    hp, maximum = active["current_hp"], active["max_hp"]
    if not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1 or not 0 < hp <= maximum:
        return _result("incomplete", "leftovers_current_hp_authority")
    recovery = maximum // 16
    post = min(maximum, hp + recovery)
    active["current_hp"] = post
    _sync_hp(state, side, post, maximum)
    return {"status": "resolved", "trace": {"effect": "leftovers_recovery", "owner": deepcopy(owners[side]), "item": "leftovers", "pre_hp": hp, "max_hp": maximum, "recovery": recovery, "post_hp": post, "execution_status": "executed" if post != hp else "prevented", "outcome": "recovered" if post != hp else "already_full_hp", "provenance": "detached_branch_leftovers_recovery_v1"}}


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
