"""Strict post-hit authority for deterministic target effects of thrown Fling items."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata
from llm.advisor_runtime_d0_contact_reactive_status_authority import (
    _current_modifier_authorities, _prevention, _runtime_type_authority,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_current_condition_authority, runtime_strategy_d0_freshness,
)


SCHEMA_VERSION = "runtime-d0-fling-item-bound-deterministic-target-effect-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_STATUS = frozenset({"paralysis", "poison", "toxic", "burn"})


def freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    fling_execution_authority: Mapping[str, Any], source_leaf: Mapping[str, Any],
    pending_target_action: Mapping[str, Any] | None = None,
    action_order: str | None = None,
) -> dict[str, Any]:
    """Freeze one item-specific Fling post-hit target effect.

    This deliberately consumes a leaf after Fling's ordinary damage and does
    not alter Fling Core's throw, hit, or damage behavior.
    """
    base = _base(strategy_d0, fling_execution_authority)
    if base is None:
        return _result("rejected", "fling_target_effect_execution_binding_invalid", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    record = resolve_canonical_fling_item_metadata(base["item_id"])
    if record.get("status") != "resolved" or record != fling_execution_authority.get("fling_item_metadata"):
        return _result("rejected", "fling_target_effect_manifest_binding_invalid", base)
    effect = record.get("effect")
    if not isinstance(effect, Mapping) or effect.get("kind") not in {"major_status", "flinch"}:
        return _result("unsupported", "fling_target_effect_kind_not_deterministic_supported", base, fling_item_metadata=record)
    source = _source_leaf(source_leaf, base)
    if isinstance(source, str):
        return _result("rejected", source, base, fling_item_metadata=record)
    common = {"fling_item_metadata": deepcopy(record), "source_fling_leaf": deepcopy(dict(source_leaf)), "source_hit": deepcopy(source)}
    if source["outcome"] != "successful_target_hit":
        return _terminal("not_applicable", source["reason"], base, common)
    if effect["kind"] == "major_status":
        return _major_status(strategy_d0, runtime_snapshot, base, effect, common)
    return _flinch(base, effect, common, pending_target_action, action_order)


def materialize_detached_fling_item_bound_deterministic_target_effect(*, authority: Mapping[str, Any]) -> dict[str, Any]:
    """Create only a leaf-bound hypothetical result; never mutate runtime/D0."""
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION:
        return {"status": "rejected", "reason": "invalid_fling_target_effect_authority"}
    if authority.get("status") != "resolved":
        return {"status": authority.get("status", "rejected"), "reason": authority.get("reason", "fling_target_effect_authority_unavailable")}
    outcome, effect = authority.get("outcome"), authority.get("effect")
    if outcome == "applied_major_status" and isinstance(effect, Mapping):
        condition = effect.get("condition")
        if condition not in _STATUS:
            return {"status": "rejected", "reason": "fling_target_effect_condition_invalid"}
        return {"status": "resolved", "outcome": outcome, "authority": deepcopy(dict(authority)),
                "hypothetical_target_condition": {"schema_version": "detached-hypothetical-current-condition-v1", "previous_condition": {"status": "known_none"}, "resulting_condition": condition, "source_fling_item": authority["item_id"], "source_fling_leaf_id": authority["source_fling_leaf"]["leaf_id"], "provenance": "fling_item_bound_deterministic_major_status_v1"}}
    if outcome == "applied_flinch_pending_action" and isinstance(effect, Mapping):
        return {"status": "resolved", "outcome": outcome, "authority": deepcopy(dict(authority)),
                "hypothetical_target_flinch": {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched", "source_fling_item": authority["item_id"], "pending_action_id": authority["pending_target_action"]["action_id"], "provenance": "fling_item_bound_deterministic_flinch_v1"}}
    if outcome in {"no_transition_already_statused", "prevented", "not_applicable", "flinch_no_pending_action"}:
        return {"status": "resolved", "outcome": outcome, "authority": deepcopy(dict(authority)), "no_target_effect": True}
    return {"status": "rejected", "reason": "fling_target_effect_outcome_invalid"}


def _major_status(d0: Mapping[str, Any], snapshot: Mapping[str, Any], base: Mapping[str, Any], effect: Mapping[str, Any], common: Mapping[str, Any]) -> dict[str, Any]:
    condition = effect.get("condition")
    if condition not in _STATUS:
        return _result("rejected", "fling_target_effect_condition_invalid", base, **common)
    current = freeze_runtime_current_condition_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=base["target"])
    if current.get("status") != "resolved":
        return _result(current.get("status", "incomplete"), current.get("reason", "fling_target_condition_unknown"), base, **common)
    state = current.get("condition")
    if not isinstance(state, Mapping) or state.get("status") not in {"known_none", "known_present"}:
        return _result("incomplete", "fling_target_condition_unknown", base, **common, target_condition_authority=current)
    common = {**common, "target_condition_authority": deepcopy(current)}
    if state["status"] == "known_present":
        return _terminal("no_transition_already_statused", "target_major_status_present", base, common, effect=effect, target_condition_after=deepcopy(state))
    types = _runtime_type_authority(snapshot, base["target"])
    modifiers = _current_modifier_authorities(snapshot, base["target"])
    if types.get("status") != "resolved" or modifiers is None:
        return _result("incomplete", "fling_target_status_applicability_unknown", base, **common, target_type_authority=types)
    prevention = _prevention(condition, types, modifiers)
    common = {**common, "target_type_authority": deepcopy(types), "target_modifier_authorities": deepcopy(modifiers), "status_prevention_authority": deepcopy(prevention)}
    if prevention.get("outcome") == "prevented":
        return _terminal("prevented", prevention.get("reason", "target_status_prevented"), base, common, effect=effect, target_condition_after=deepcopy(state))
    return _terminal("applied_major_status", "fling_item_deterministic_status_applied", base, common, effect=effect, target_condition_after={"status": "known_present", "condition": condition})


def _flinch(base: Mapping[str, Any], effect: Mapping[str, Any], common: Mapping[str, Any], pending: Mapping[str, Any] | None, action_order: str | None) -> dict[str, Any]:
    if pending is None:
        return _terminal("flinch_no_pending_action", "target_has_no_pending_later_action", base, common, effect=effect)
    if action_order != "own_first" or not isinstance(pending, Mapping) or pending.get("action_type") not in {"attack", "status_protection", "protection"} or not isinstance(pending.get("action_id"), str) or not pending["action_id"] or pending.get("actor") != base["target"]:
        return _result("rejected", "fling_flinch_pending_action_binding_invalid", base, **common)
    return _terminal("applied_flinch_pending_action", "fling_item_deterministic_flinch_applied", base, common, effect=effect, pending_target_action=deepcopy(dict(pending)), action_order=action_order)


def _source_leaf(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("candidate_id") != base["action_id"] or not isinstance(value.get("leaf_id"), str) or not isinstance(value.get("provenance"), Mapping):
        return "fling_target_effect_source_leaf_invalid"
    provenance, consequences = value["provenance"], value.get("consequences")
    if any(provenance.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "attacker", "target")) or provenance.get("move_id") != "fling" or provenance.get("fling_execution_authority") != base["execution_authority"]:
        return "fling_target_effect_source_leaf_binding_mismatch"
    if value.get("hit_state") != "hit" or not isinstance(consequences, Mapping):
        return {"outcome": "inapplicable", "reason": "fling_miss_or_pre_execution_cancellation"}
    hit = consequences.get("source_hit_context")
    if not isinstance(hit, Mapping) or hit.get("source_action_id") != base["action_id"] or hit.get("source_move_id") != "fling":
        return "fling_target_effect_source_hit_missing"
    if hit.get("target_routing") != "target":
        return {"outcome": "inapplicable", "reason": "fling_target_effect_substitute_or_non_target_route"}
    if not isinstance(hit.get("actual_damage"), int) or hit["actual_damage"] <= 0:
        return {"outcome": "inapplicable", "reason": "fling_protect_or_immunity_or_no_damage"}
    if consequences.get("target_ko") is True or not isinstance(consequences.get("target_final_hp"), int) or consequences["target_final_hp"] <= 0:
        return {"outcome": "inapplicable", "reason": "fling_target_fainted_before_effect"}
    return {"outcome": "successful_target_hit", "reason": None, "target_routing": "target", "actual_damage": hit["actual_damage"], "target_post_hp": consequences["target_final_hp"], "source_leaf_id": value["leaf_id"]}


def _base(d0: Any, execution: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(execution, Mapping) or execution.get("status") != "resolved" or execution.get("schema_version") != "runtime-d0-fling-item-execution-authority-v1" or execution.get("outcome") != "ready_throw":
        return None
    actor, target, item = execution.get("actor"), execution.get("target"), execution.get("user_item_before")
    if not _owner(actor) or not _owner(target) or actor != d0.get("decision_owner") or not isinstance(item, Mapping) or item.get("status") != "known" or not isinstance(item.get("value"), str) or not item["value"] or execution.get("move_id") != "fling" or execution.get("action_id") is None or execution.get("item_after") != {"state": "known_absent", "item": None}:
        return None
    expected = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "actor": actor, "target": target}
    if any(execution.get(key) != value for key, value in expected.items()):
        return None
    return {**deepcopy(expected), "attacker": deepcopy(dict(actor)), "item_id": item["value"], "action_id": execution["action_id"], "move_id": "fling", "execution_authority": deepcopy(dict(execution))}


def _terminal(outcome: str, reason: str, base: Mapping[str, Any], common: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), **deepcopy(dict(common)), **deepcopy(extra), "outcome": outcome, "reason": reason, "provenance": "runtime_d0_fling_item_bound_deterministic_target_effect_v1"}
def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), **deepcopy(extra), "reason": reason}
def _owner(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
