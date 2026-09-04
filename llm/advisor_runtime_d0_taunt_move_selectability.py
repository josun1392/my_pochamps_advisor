"""Strict new-decision Taunt selectability consumer; never rewrites intent."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_runtime_d0_taunt_restriction_authority import SCHEMA_VERSION as TAUNT_SCHEMA

SCHEMA_VERSION = "runtime-d0-taunt-move-selectability-authority-v1"


def resolve_taunt_move_selectability(*, taunt_authority: Mapping[str, Any], owner: Mapping[str, Any], move_metadata_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Taunt-only legal status for a future decision point."""
    meta = move_metadata_authority.get("metadata") if isinstance(move_metadata_authority, Mapping) else None
    if not isinstance(meta, Mapping) or not isinstance(meta.get("move_id"), str) or not meta["move_id"] or meta.get("category") not in {"physical", "special", "status"}:
        return _result("incomplete", "move_category_authority_missing", owner)
    if not isinstance(taunt_authority, Mapping) or taunt_authority.get("schema_version") != TAUNT_SCHEMA:
        return _result("incomplete", "current_taunt_authority_missing", owner)
    if taunt_authority.get("status") != "resolved":
        return _result(taunt_authority.get("status", "rejected"), taunt_authority.get("reason", "current_taunt_authority_unavailable"), owner)
    if not isinstance(owner, Mapping) or taunt_authority.get("owner") != dict(owner): return _result("rejected", "taunt_authority_owner_binding_mismatch", owner)
    expected = {key: taunt_authority.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")}
    expected["active_attacker"] = dict(owner)
    if not isinstance(move_metadata_authority, Mapping) or move_metadata_authority.get("status") != "resolved" or any(move_metadata_authority.get(key) != value for key, value in expected.items()):
        return _result("rejected", "move_metadata_authority_binding_mismatch", owner)
    if taunt_authority.get("state") not in {"active", "not_active"}:
        return _result("rejected", "taunt_authority_state_invalid", owner)
    active = taunt_authority["state"] == "active"
    restricted = active and meta["category"] == "status"
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"owner":deepcopy(dict(owner)),"move_id":meta.get("move_id"),"move_category":meta["category"],"selectability":"not_selectable" if restricted else "selectable","reason":"taunt_status_move_restricted" if restricted else "taunt_does_not_restrict_move","taunt_authority":deepcopy(dict(taunt_authority)),"provenance":"strict_current_d0_taunt_new_decision_selectability_v1"}


def _result(status: str, reason: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    return {"status":status,"schema_version":SCHEMA_VERSION,"owner":deepcopy(dict(owner)) if isinstance(owner, Mapping) else None,"reason":reason}
