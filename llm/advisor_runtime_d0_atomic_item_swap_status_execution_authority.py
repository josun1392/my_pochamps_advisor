"""Strict D0 authority for a catalogued, non-damaging atomic item swap."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_atomic_item_swap_status import (
    resolve_atomic_item_swap_side_legality, resolve_canonical_atomic_item_swap_status_move,
)
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-atomic-item-swap-status-execution-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def freeze_runtime_d0_atomic_item_swap_status_execution_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], execution_applicability_authority: Mapping[str, Any] | None) -> dict[str, Any]:
    base = _base(strategy_d0, action, actor, target)
    if base is None:
        return _result("rejected", "atomic_item_swap_identity_or_d0_invalid", {})
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current":
        return _result("rejected", "stale_runtime_d0", base)
    move = _move(action)
    canonical = resolve_canonical_atomic_item_swap_status_move(move=move)
    if canonical.get("status") != "resolved":
        return _result(canonical.get("status", "rejected"), canonical.get("reason", "atomic_item_swap_move_unavailable"), base, canonical_move=canonical)
    applicability = _applicability(execution_applicability_authority, base)
    if isinstance(applicability, Mapping) and applicability.get("error"):
        return _result(applicability["status"], applicability["reason"], base, canonical_move=canonical)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    actor_raw, target_raw = _pokemon(state, actor), _pokemon(state, target)
    if actor_raw is None or target_raw is None:
        return _result("rejected", "atomic_item_swap_runtime_identity_mismatch", base, canonical_move=canonical)
    actor_item, target_item = _item_authority(actor_raw, actor, base), _item_authority(target_raw, target, base)
    common = {"canonical_move": deepcopy(canonical), "execution_applicability_authority": deepcopy(execution_applicability_authority),
              "execution_applicability": deepcopy(applicability), "actor_item_authority": actor_item, "target_item_authority": target_item,
              "actor_item_before": _before(actor_item), "target_item_before": _before(target_item)}
    if actor_item["status"] == "unknown" or target_item["status"] == "unknown":
        return _terminal("incomplete_authority", "incomplete", "atomic_item_swap_item_authority_unknown", base, common)
    abilities = _ability_and_suppression(actor_raw, target_raw, actor, target, base)
    common["ability_authority"] = abilities
    if abilities["status"] != "resolved":
        return _terminal("incomplete_authority", "incomplete", "atomic_item_swap_ability_or_suppression_unknown", base, common)
    if applicability["outcome"] == "blocked":
        return _terminal("blocked_protection", "resolved", "status_action_protection_blocked", base, common)
    if applicability["outcome"] != "ordinary":
        return _terminal("incomplete_authority", "incomplete", "atomic_item_swap_targeting_or_substitute_unresolved", base, common)
    actor_species, target_species = actor_raw.get("pokemon_id"), target_raw.get("pokemon_id")
    actor_legality = resolve_atomic_item_swap_side_legality(holder_item_authority=actor_item, holder_species=actor_species, incoming_item_authority=target_item)
    target_legality = resolve_atomic_item_swap_side_legality(holder_item_authority=target_item, holder_species=target_species, incoming_item_authority=actor_item)
    common["actor_legality_authority"], common["target_legality_authority"] = actor_legality, target_legality
    if actor_legality.get("status") != "resolved" or target_legality.get("status") != "resolved":
        return _terminal("incomplete_authority", "incomplete", "atomic_item_swap_legality_unknown", base, common)
    if abilities["sticky_hold_active"]:
        return _terminal("blocked_sticky_hold", "resolved", "target_sticky_hold_active", base, common)
    if actor_item["status"] == target_item["status"] == "known_absent":
        return _terminal("failed_both_no_item", "resolved", "both_holders_known_absent", base, common)
    if not all((actor_legality["transferable"], target_legality["transferable"], actor_legality["allowed_to_receive"], target_legality["allowed_to_receive"])):
        return _terminal("failed_item_restriction", "resolved", "atomic_item_swap_item_restriction", base, common)
    outcome = "swap_two_items" if actor_item["status"] == target_item["status"] == "known" else "give_actor_item" if actor_item["status"] == "known" else "take_target_item"
    common["transition_kind"] = outcome
    common["actor_item_after"], common["target_item_after"] = _before(target_item), _before(actor_item)
    return _terminal("executed_swap", "resolved", outcome, base, common)


def _base(d0: Any, action: Any, actor: Any, target: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(actor) or not _owner(target) or not isinstance(action, Mapping): return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or actor != d0.get("decision_owner") or active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target) or actor.get("side") == target.get("side"): return None
    action_id, selected = action.get("action_id"), action.get("identity")
    if action.get("action_type") != "attack" or not isinstance(action_id, str) or not action_id or not isinstance(selected, str) or not selected: return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(d0["decision_owner"])), "actor": deepcopy(dict(actor)), "target": deepcopy(dict(target)), "action_id": action_id, "selected_move_id": selected, "execution_move_id": selected, "move_id": selected, "move_family": "atomic_item_swap_status"}


def _move(action: Mapping[str, Any]) -> Mapping[str, Any]:
    source = action.get("move_metadata_authority") or action.get("metadata_authority")
    return source.get("metadata") if isinstance(source, Mapping) and source.get("status") == "resolved" and isinstance(source.get("metadata"), Mapping) else {}


def _applicability(value: Any, base: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping): return {"error": True, "status": "incomplete", "reason": "status_execution_applicability_authority_required"}
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "actor", "target", "action_id", "move_id"):
        expected = base["execution_move_id"] if key == "move_id" else base[key]
        if value.get(key) != expected: return {"error": True, "status": "rejected", "reason": "status_execution_applicability_binding_mismatch"}
    if value.get("status") != "resolved": return {"error": True, "status": "incomplete", "reason": "status_execution_applicability_unavailable"}
    outcome = value.get("outcome")
    if outcome == "prevented": outcome = "blocked"
    if outcome not in {"ordinary", "blocked"}: return {"error": True, "status": "incomplete", "reason": "status_execution_targeting_or_substitute_unresolved"}
    return {"outcome": outcome, "authority": deepcopy(dict(value))}


def _item_authority(raw: Mapping[str, Any], owner: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    value, provenance = raw.get("known_item"), raw.get("known_item_provenance")
    common = {"owner": deepcopy(dict(owner)), "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "runtime_item_provenance": deepcopy(provenance) if isinstance(provenance, Mapping) else None}
    if isinstance(value, str) and value and not is_unknown_battle_fact(value): return {"status": "known", "value": value, **common}
    if value is None and isinstance(provenance, Mapping) and provenance.get("event_kind") in {"current_item_observed", "current_opponent_switch_target_combat_observed", "item_consumption_observed", "item_removed_observed"}: return {"status": "known_absent", "value": None, **common}
    return {"status": "unknown", "value": None, **common}


def _ability_and_suppression(actor_raw: Mapping[str, Any], target_raw: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    def one(raw: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
        value, provenance = raw.get("current_ability"), raw.get("current_ability_provenance")
        common = {"owner": deepcopy(dict(owner)), "runtime_ability_provenance": deepcopy(provenance) if isinstance(provenance, Mapping) else None}
        return {"status": "known", "value": value, **common} if isinstance(value, str) and value and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_ability_observed" and provenance.get("trust") == "user_confirmed_observation" else {"status": "unknown", **common}
    actor_ability, target_ability = one(actor_raw, actor), one(target_raw, target)
    if actor_ability["status"] != "known" or target_ability["status"] != "known": return {"status": "incomplete", "actor": actor_ability, "target": target_ability}
    gas = actor_ability["value"] == "neutralizing-gas" or target_ability["value"] == "neutralizing-gas"
    return {"status": "resolved", "actor": actor_ability, "target": target_ability, "neutralizing_gas_active": gas, "sticky_hold_active": target_ability["value"] == "sticky-hold" and not gas, "provenance": "runtime_d0_atomic_item_swap_ability_suppression_v1", "binding": {key: deepcopy(base[key]) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "actor", "target")}}


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; raw = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return raw if isinstance(raw, Mapping) and raw.get("pokemon_id") == owner["pokemon_id"] else None
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _before(value: Mapping[str, Any]) -> dict[str, Any]: return {"state": "known_present", "item": value["value"]} if value.get("status") == "known" else {"state": "known_absent", "item": None} if value.get("status") == "known_absent" else {"state": "unknown", "item": None}
def _terminal(outcome: str, status: str, reason: str, base: Mapping[str, Any], common: Mapping[str, Any]) -> dict[str, Any]:
    result = {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), **deepcopy(dict(common)), "outcome": outcome, "reason": reason, "provenance": "strict_runtime_d0_atomic_item_swap_status_execution_freeze_v1"}
    # Every terminal outcome preserves one auditable, coherent item-after pair;
    # non-successes are exact identity transitions rather than absent fields.
    result.setdefault("actor_item_after", deepcopy(result.get("actor_item_before")))
    result.setdefault("target_item_after", deepcopy(result.get("target_item_before")))
    return result
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
