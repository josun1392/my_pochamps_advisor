"""Narrow Focus Sash post-hit survival and consumption projection."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def focus_sash_state(authority: Mapping[str, Any] | None, *, consumed: bool) -> dict[str, Any]:
    if not isinstance(authority, Mapping):
        return {"state": "not_applicable", "authority_present": False}
    if authority.get("status") == "ready":
        return {
            "state": "consumed" if consumed else "available",
            "authority_present": True,
            "holder": deepcopy(authority.get("holder")),
            "item_before": "focus-sash",
            "item_after": {"status": "known_absent", "value": None} if consumed else {"status": "known", "value": "focus-sash"},
        }
    if authority.get("outcome") == "known_no_effect":
        return {"state": "known_no_effect", "authority_present": True, "reason": authority.get("reason")}
    return {"state": "unavailable", "authority_present": True, "reason": authority.get("reason")}


def apply_focus_sash_to_hit(
    *, authority: Mapping[str, Any] | None, consumed: bool, hp_before: int,
    raw_damage: int, actual_damage: int, source_hit: Mapping[str, Any],
) -> dict[str, Any]:
    """Return exact actual damage plus Focus Sash activation provenance."""
    base = {"outcome": "not_applicable"}
    if authority is None:
        return {"actual_damage": actual_damage, "post_hp": max(0, hp_before - actual_damage), "activated": False, "consumed": consumed, "survival": base}
    if not isinstance(authority, Mapping) or authority.get("schema_version") != "runtime-d0-focus-sash-survival-authority-v1":
        return {"status": "rejected", "reason": "focus_sash_survival_authority_invalid"}
    status = authority.get("status")
    if status in {"incomplete", "unsupported", "rejected"}:
        return {"status": status, "reason": authority.get("reason", "focus_sash_survival_authority_unavailable")}
    if status != "ready":
        return {"actual_damage": actual_damage, "post_hp": max(0, hp_before - actual_damage), "activated": False, "consumed": consumed, "survival": {"outcome": "not_triggered", "reason": authority.get("reason")}}
    if consumed:
        return {"actual_damage": actual_damage, "post_hp": max(0, hp_before - actual_damage), "activated": False, "consumed": True, "survival": {"outcome": "already_consumed", "reason": "already_consumed", "item_after": {"status": "known_absent", "value": None}}}
    if authority.get("current_hp") != hp_before or authority.get("maximum_hp") != hp_before:
        return {"status": "rejected", "reason": "focus_sash_hp_binding_mismatch"}
    if raw_damage < hp_before:
        return {"actual_damage": actual_damage, "post_hp": max(0, hp_before - actual_damage), "activated": False, "consumed": False, "survival": {"outcome": "not_triggered", "reason": "nonlethal_damage"}}
    projected = max(0, hp_before - 1)
    return {
        "actual_damage": projected, "post_hp": 1, "activated": True, "consumed": True,
        "survival": {
            "outcome": "applied", "item_before": "focus-sash", "item_after": {"status": "known_absent", "value": None},
            "focus_sash_eligible": True, "target_final_hp": 1,
            "hp_before": hp_before, "pre_survival_lethal": True,
            "raw_damage": raw_damage, "actual_damage": projected,
            "holder": deepcopy(authority.get("holder")),
            "source_hit": deepcopy(dict(source_hit)),
            "provenance": "exact_detached_focus_sash_survival_consumption_v1",
        },
    }
