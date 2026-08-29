"""Strict D0-bound Quick Guard priority-action applicability authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_quick_guard_protection import canonical_quick_guard_protection_metadata
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.narrow_action_order import evaluate_action_order

SCHEMA_VERSION = "runtime-d0-quick-guard-priority-applicability-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def build_quick_guard_protection_context(*, session_id: str, guard_user: Mapping[str, Any], guard_action_id: str, incoming_actor: Mapping[str, Any], incoming_action_id: str, incoming_move_id: str, selected_target: Mapping[str, Any], protection_authority: Mapping[str, Any], action_blocked: bool, protection_bypass: bool) -> dict[str, Any]:
    guard, incoming, target = _owner(guard_user), _owner(incoming_actor), _owner(selected_target)
    if not isinstance(session_id, str) or not session_id or guard["side"] == incoming["side"] or target != guard or not all(isinstance(value, str) and value for value in (guard_action_id, incoming_action_id, incoming_move_id)) or not isinstance(action_blocked, bool) or not isinstance(protection_bypass, bool) or not _protection(protection_authority, guard):
        raise ValueError("invalid_quick_guard_protection_context")
    return {"schema_version": "quick-guard-protection-context-v1", "session_id": session_id, "guard_user": guard, "guard_action_id": guard_action_id, "guard_move_id": "quick-guard", "incoming_actor": incoming, "incoming_action_id": incoming_action_id, "incoming_move_id": incoming_move_id, "selected_target": target, "protection_authority": deepcopy(dict(protection_authority)), "action_blocked": action_blocked, "protection_bypass": protection_bypass, "provenance": "explicit_existing_quick_guard_protection_context_v1"}


def freeze_runtime_d0_quick_guard_priority_applicability_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], guard_user: Mapping[str, Any], guard_action_id: str, incoming_actor: Mapping[str, Any], incoming_action: Mapping[str, Any], selected_target: Mapping[str, Any], protection_context: Mapping[str, Any] | None) -> dict[str, Any]:
    base = _base(strategy_d0, guard_user, guard_action_id, incoming_actor, incoming_action, selected_target)
    if base is None: return _result("rejected", "invalid_runtime_d0_or_quick_guard_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    context = _context(protection_context, base)
    if context is None: return _result("rejected", "quick_guard_protection_context_binding_mismatch", base)
    if not context["action_blocked"] or context["protection_bypass"]: return _no(base, context, "protection_failed_or_bypassed")
    metadata = incoming_action.get("move_metadata_authority", {}).get("metadata") if isinstance(incoming_action, Mapping) and isinstance(incoming_action.get("move_metadata_authority"), Mapping) else None
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != base["incoming_move_id"]: return _result("incomplete", "quick_guard_incoming_move_metadata_missing", base)
    if metadata.get("category") not in {"physical", "special"} or metadata.get("target") not in {"selected-pokemon", "normal"}: return _result("incomplete", "quick_guard_action_applicability_unknown", base)
    priority = _effective_priority(runtime_snapshot, base["incoming_actor"], metadata)
    if priority.get("status") != "resolved": return _result(priority["status"], priority["reason"], base)
    if priority["effective_priority"] <= 0: return _no(base, context, "incoming_action_not_positive_priority", priority=priority)
    if canonical_quick_guard_protection_metadata("quick-guard") is None: return _result("rejected", "canonical_quick_guard_metadata_invalid", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": "applies", "effective_priority_authority": priority, "protection_context": context, "provenance": "runtime_d0_canonical_quick_guard_positive_priority_applicability_v1"}


def _effective_priority(snapshot: Mapping[str, Any], owner: Mapping[str, Any], metadata: Mapping[str, Any]) -> dict[str, Any]:
    row = _pokemon(snapshot, owner)
    if row is None: return {"status": "rejected", "reason": "quick_guard_incoming_runtime_identity_mismatch"}
    ability, provenance = row.get("current_ability"), row.get("current_ability_provenance")
    if not isinstance(ability, str) or not ability or not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_ability_observed" or provenance.get("trust") != "user_confirmed_observation": return {"status": "incomplete", "reason": "quick_guard_priority_ability_unknown"}
    hp, maximum = row.get("current_hp"), row.get("max_hp")
    full_hp = "full" if isinstance(hp, int) and not isinstance(hp, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and hp == maximum and hp > 0 else "not_full" if isinstance(hp, int) and not isinstance(hp, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and 0 <= hp < maximum else "unknown"
    engine = evaluate_action_order(self_action={"move_id": metadata.get("move_id"), "priority": metadata.get("priority"), "category": metadata.get("category"), "type": metadata.get("type"), "triage_healing": metadata.get("triage_healing", "omitted")}, opponent_action={"move_id": "quick-guard-priority-reference", "priority": -7, "category": "status", "type": "normal"}, self_final_speed=1, opponent_final_speed=1, self_priority_ability=ability, opponent_priority_ability="static", self_gale_wings_full_hp=full_hp)
    value = engine.get("self_priority")
    if engine.get("status") == "unsupported_mechanic": return {"status": "incomplete", "reason": engine.get("unsupported_reason", "quick_guard_priority_modifier_unsupported")}
    if not isinstance(value, int) or isinstance(value, bool): return {"status": "incomplete", "reason": (engine.get("missing_inputs") or ["quick_guard_effective_priority_unknown"])[0]}
    return {"status": "resolved", "base_priority": metadata.get("priority"), "effective_priority": value, "priority_engine": deepcopy(engine), "provenance": "narrow_priority_calculation_not_action_order_authority_v1"}


def _base(d0: Any, guard: Any, guard_action: Any, incoming: Any, action: Any, target: Any) -> dict[str, Any] | None:
    try: guard_owner, incoming_owner, selected = _owner(guard), _owner(incoming), _owner(target)
    except ValueError: return None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or guard_owner["side"] == incoming_owner["side"] or selected != guard_owner or not isinstance(guard_action, str) or not guard_action or not isinstance(action, Mapping) or not isinstance(action.get("action_id"), str) or not isinstance(action.get("identity"), str): return None
    if d0.get("active_owners", {}).get(guard_owner["side"]) != guard_owner or d0.get("active_owners", {}).get(incoming_owner["side"]) != incoming_owner: return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "guard_user": guard_owner, "guard_action_id": guard_action, "guard_move_id": "quick-guard", "incoming_actor": incoming_owner, "incoming_action_id": action["action_id"], "incoming_move_id": action["identity"], "selected_target": selected}


def _context(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return None
    try: expected = build_quick_guard_protection_context(session_id=base["session_id"], guard_user=base["guard_user"], guard_action_id=base["guard_action_id"], incoming_actor=base["incoming_actor"], incoming_action_id=base["incoming_action_id"], incoming_move_id=base["incoming_move_id"], selected_target=base["selected_target"], protection_authority=value.get("protection_authority"), action_blocked=value.get("action_blocked"), protection_bypass=value.get("protection_bypass"))
    except (TypeError, ValueError): return None
    return expected if value == expected else None


def _pokemon(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None; side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None; roster = side.get("pokemon") if isinstance(side, Mapping) else None; row = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    return row if isinstance(row, Mapping) and row.get("pokemon_id") == owner.get("pokemon_id") else None
def _protection(value: Any, owner: Mapping[str, Any]) -> bool: return isinstance(value, Mapping) and value.get("status") == "resolved" and value.get("owner") == owner and isinstance(value.get("metadata"), Mapping) and value["metadata"].get("move_id") == "quick-guard"
def _owner(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_OWNER_KEYS) or not isinstance(value.get("session_id"), str) or not value["session_id"] or value.get("side") not in {"self", "opponent"} or not isinstance(value.get("slot_index"), int) or isinstance(value["slot_index"], bool) or value["slot_index"] < 0 or not isinstance(value.get("pokemon_id"), str) or not value["pokemon_id"]: raise ValueError("invalid_quick_guard_owner")
    return deepcopy(dict(value))
def _no(base: Mapping[str, Any], context: Mapping[str, Any], reason: str, *, priority: Mapping[str, Any] | None = None) -> dict[str, Any]: return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "reason": reason, "protection_context": deepcopy(dict(context)), **({"effective_priority_authority": deepcopy(dict(priority))} if priority else {}), "provenance": "runtime_d0_canonical_quick_guard_no_effect_v1"}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
