"""Strict runtime/D0 authority for one live own manual-switch entry."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_roster_mechanics import (
    active_self_roster_mechanics_view,
    build_self_roster_mechanics_context_projection,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_switch_hazard_authority import project_switch_hazard_context


SCHEMA_VERSION = "runtime-d0-manual-switch-entry-authority-v1"


def freeze_runtime_d0_manual_switch_entry_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], incoming_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze only the existing entry-engine inputs for one selected own bench owner."""
    owner = incoming_authority.get("owner") if isinstance(incoming_authority, Mapping) else None
    if not _d0(strategy_d0) or not _owner(owner) or owner.get("side") != "self":
        return _result("rejected", "invalid_live_manual_switch_entry_request")
    if incoming_authority.get("status") != "resolved" or incoming_authority.get("source_branch_fingerprint") != strategy_d0["strategy_preview_fingerprint"]:
        return _result("rejected", "live_manual_switch_incoming_binding_mismatch")
    if incoming_authority.get("decision_owner") != strategy_d0["decision_owner"] or owner == strategy_d0["decision_owner"]:
        return _result("rejected", "live_manual_switch_incoming_owner_mismatch")
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0")
    state = runtime_snapshot.get("state")
    if not isinstance(state, Mapping):
        return _result("rejected", "runtime_state_unavailable")
    try:
        roster = build_self_roster_mechanics_context_projection(state)
    except ValueError:
        return _result("rejected", "runtime_roster_mechanics_invalid")
    target = active_self_roster_mechanics_view(roster, slot_index=owner["slot_index"], pokemon_id=owner["pokemon_id"])
    hp = incoming_authority.get("hp_authority")
    if not isinstance(target, Mapping) or not isinstance(hp, Mapping) or target.get("hp_authority", {}).get("status") != "known" or any(target["hp_authority"].get(key) != hp.get(key) for key in ("current_hp", "maximum_hp")):
        return _result("rejected", "live_manual_switch_target_hp_mismatch")
    entry = {
        "hazards": project_switch_hazard_context(state, affected_side="self"),
        "target_roster_mechanics": target,
        "intimidate_authority": deepcopy(state.get("switch_entry_intimidate_authority")),
        "download_authority": deepcopy(state.get("switch_entry_download_authority")),
        "trace_authority": deepcopy(state.get("switch_entry_trace_authority")),
        "sturdy_authority": deepcopy(state.get("switch_entry_sturdy_authority")),
        "field_state_context": deepcopy(state.get("field_state_context")),
    }
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION,
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "incoming_owner": deepcopy(dict(owner)),
        "entry_authority": entry,
        "provenance": "runtime_battle_state_v1_to_live_manual_switch_entry_authority_v1",
    }


def valid_runtime_d0_manual_switch_entry_authority(*, value: Any, source_branch_fingerprint: str, incoming_owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCHEMA_VERSION:
        return None
    if value.get("source_branch_fingerprint") != source_branch_fingerprint or value.get("incoming_owner") != dict(incoming_owner) or value.get("session_id") != incoming_owner.get("session_id"):
        return None
    entry = value.get("entry_authority")
    target = entry.get("target_roster_mechanics") if isinstance(entry, Mapping) else None
    hazards = entry.get("hazards") if isinstance(entry, Mapping) else None
    if not isinstance(target, Mapping) or not isinstance(hazards, Mapping) or any(target.get(key) != incoming_owner.get(key) for key in ("session_id", "side", "slot_index", "pokemon_id")) or hazards.get("affected_side") != incoming_owner.get("side"):
        return None
    return entry


def _d0(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "resolved" and isinstance(value.get("session_id"), str) and isinstance(value.get("strategy_preview_fingerprint"), str) and isinstance(value.get("decision_owner"), Mapping)


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("session_id"), str) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
