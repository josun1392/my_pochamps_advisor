"""Strict live replacement/entry handoff for one actor-neutral damage pivot."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage_pivot_moves import canonical_damage_pivot_metadata, is_canonical_damage_pivot
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_incoming_current_state_authority,
    freeze_runtime_strategy_d0,
    runtime_strategy_d0_freshness,
)
from llm.advisor_roster_mechanics import _base_record
from llm.advisor_switch_hazard_authority import project_switch_hazard_context


SCHEMA_VERSION = "runtime-d0-pivot-replacement-authority-v1"


def freeze_runtime_d0_pivot_replacement_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], pivot_actor: Mapping[str, Any], pivot_action: Mapping[str, Any], move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Select only a uniquely provable same-side bench target for a pivot.

    This is deliberately not a voluntary-switch permission.  Multiple legal
    targets are a policy boundary and remain incomplete.
    """
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or not isinstance(pivot_actor, Mapping) or not isinstance(pivot_action, Mapping):
        return _result("rejected", "pivot_replacement_request_invalid")
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0")
    metadata = canonical_damage_pivot_metadata(move_metadata)
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0.get("active_owners"), Mapping) else {}
    if not is_canonical_damage_pivot(metadata) or pivot_actor not in (active.get("self"), active.get("opponent")) or pivot_action.get("action_id") not in {f"attack:{metadata.get('move_id')}", f"opponent_attack:{metadata.get('move_id')}"}:
        return _result("rejected", "pivot_replacement_action_binding_invalid")
    pivot_d0 = freeze_runtime_strategy_d0(runtime_snapshot=runtime_snapshot, decision_owner=pivot_actor)
    if pivot_d0.get("status") != "resolved": return _result("incomplete", pivot_d0.get("reason", "pivot_actor_d0_unavailable"))
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    side_key = f"{pivot_actor.get('side')}_side"
    roster = state.get(side_key, {}).get("pokemon") if isinstance(state, Mapping) and isinstance(state.get(side_key), Mapping) else None
    if not isinstance(roster, Mapping): return _result("rejected", "pivot_replacement_roster_invalid")
    candidates = []
    for slot, row in roster.items():
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(row, Mapping) or slot == pivot_actor.get("slot_index"): continue
        pokemon_id, hp, maximum, fainted = row.get("pokemon_id"), row.get("current_hp"), row.get("max_hp"), row.get("fainted")
        if not isinstance(pokemon_id, str) or not pokemon_id or not isinstance(hp, int) or isinstance(hp, bool) or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0 or not isinstance(fainted, bool) or fainted is not (hp == 0):
            return _result("incomplete", "pivot_replacement_roster_completeness_unknown")
        if not fainted:
            candidates.append({"session_id": pivot_d0["session_id"], "side": pivot_actor["side"], "slot_index": slot, "pokemon_id": pokemon_id})
    base = {key: deepcopy(pivot_d0[key]) for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint", "decision_owner")}
    base["source_branch_fingerprint"] = base.pop("strategy_preview_fingerprint")
    base.update(pivot_actor=deepcopy(dict(pivot_actor)), pivot_action_id=pivot_action["action_id"], move_id=metadata["move_id"])
    if not candidates: return {"status": "known_none", "schema_version": SCHEMA_VERSION, **base, "reason": "pivot_no_exact_legal_replacement", "provenance": "runtime_exact_pivot_replacement_choice_v1"}
    if len(candidates) != 1: return {"status": "incomplete", "schema_version": SCHEMA_VERSION, **base, "reason": "opponent_pivot_replacement_choice_policy_required", "candidate_owners": tuple(deepcopy(candidates)), "provenance": "runtime_exact_pivot_replacement_choice_v1"}
    incoming = freeze_runtime_incoming_current_state_authority(strategy_d0=pivot_d0, runtime_snapshot=runtime_snapshot, incoming_owner=candidates[0])
    if incoming.get("status") != "resolved": return {"status": incoming.get("status", "incomplete"), "schema_version": SCHEMA_VERSION, **base, "reason": incoming.get("reason", "pivot_incoming_authority_unavailable")}
    incoming_raw = roster[candidates[0]["slot_index"]]
    target = {
        **_base_record(
            pivot_d0["session_id"], candidates[0]["slot_index"],
            candidates[0]["pokemon_id"], incoming_raw,
        ),
        "side": pivot_actor["side"],
    }
    item_provenance = incoming_raw.get("known_item_provenance")
    if (
        incoming_raw.get("known_item") is None
        and isinstance(item_provenance, Mapping)
        and item_provenance.get("event_kind") in {
            "current_item_observed",
            "current_opponent_switch_target_combat_observed",
            "item_consumption_observed",
            "item_removed_observed",
        }
        and item_provenance.get("trust") == "user_confirmed_observation"
    ):
        target["item_authority"] = {"status": "known", "value": None}
    entry = {
        "hazards": project_switch_hazard_context(state, affected_side=pivot_actor["side"]),
        "target_roster_mechanics": target,
        "intimidate_authority": deepcopy(state.get("switch_entry_intimidate_authority")),
        "download_authority": deepcopy(state.get("switch_entry_download_authority")),
        "trace_authority": deepcopy(state.get("switch_entry_trace_authority")),
        "sturdy_authority": deepcopy(state.get("switch_entry_sturdy_authority")),
        "field_state_context": deepcopy(state.get("field_state_context")),
    }
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "owner": deepcopy(candidates[0]), "incoming_authority": incoming, "entry_authority": entry, "provenance": "runtime_exact_actor_neutral_pivot_replacement_v1"}


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
