"""Strict D0-bound Wide Guard applicability over frozen doubles recipients."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_wide_guard_protection import canonical_wide_guard_protection_metadata
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness

SCHEMA_VERSION = "runtime-d0-wide-guard-spread-applicability-authority-v1"
TARGET_SET_SCHEMA = "runtime-d0-doubles-action-target-set-authority-v1"
SCOPE_SCHEMA = "runtime-d0-multi-recipient-action-execution-scope-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def build_wide_guard_protection_context(*, session_id: str, guard_user: Mapping[str, Any], guard_action_id: str, incoming_actor: Mapping[str, Any], incoming_action_id: str, incoming_move_id: str, protected_side: str, protection_authority: Mapping[str, Any], action_blocked: bool, protection_bypass: bool) -> dict[str, Any]:
    guard, incoming = _owner(guard_user), _owner(incoming_actor)
    if not isinstance(session_id, str) or not session_id or guard["side"] == incoming["side"] or protected_side != guard["side"] or not all(isinstance(value, str) and value for value in (guard_action_id, incoming_action_id, incoming_move_id)) or not isinstance(action_blocked, bool) or not isinstance(protection_bypass, bool) or not _protection(protection_authority, guard):
        raise ValueError("invalid_wide_guard_protection_context")
    return {"schema_version": "wide-guard-protection-context-v1", "session_id": session_id, "guard_user": guard, "guard_action_id": guard_action_id, "guard_move_id": "wide-guard", "incoming_actor": incoming, "incoming_action_id": incoming_action_id, "incoming_move_id": incoming_move_id, "protected_side": protected_side, "protection_authority": deepcopy(dict(protection_authority)), "action_blocked": action_blocked, "protection_bypass": protection_bypass, "provenance": "explicit_existing_wide_guard_protection_context_v1"}


def freeze_runtime_d0_wide_guard_spread_applicability_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], guard_user: Mapping[str, Any], guard_action_id: str, incoming_action: Mapping[str, Any], protected_side: str, decision_point: str, target_set_authority: Mapping[str, Any] | None, execution_scope_authority: Mapping[str, Any] | None, protection_context: Mapping[str, Any] | None) -> dict[str, Any]:
    base = _base(strategy_d0, guard_user, guard_action_id, incoming_action, protected_side, decision_point)
    if base is None: return _result("rejected", "invalid_runtime_d0_or_wide_guard_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    context = _context(protection_context, base)
    if context is None: return _result("rejected", "wide_guard_protection_context_binding_mismatch", base)
    if canonical_wide_guard_protection_metadata("wide-guard") is None: return _result("rejected", "canonical_wide_guard_metadata_invalid", base)
    target_set = _target_set(target_set_authority, base)
    if isinstance(target_set, str): return _result("rejected" if target_set.endswith("mismatch") else "incomplete", target_set, base)
    if not context["action_blocked"]: return _no(base, context, target_set, "wide_guard_failed")
    if context["protection_bypass"]: return _no(base, context, target_set, "incoming_action_bypasses_wide_guard")
    if target_set["recipient_classification"] != "spread_multi_target": return _no(base, context, target_set, "incoming_action_not_spread")
    scope = _scope(execution_scope_authority, base, target_set_authority)
    if isinstance(scope, str): return _result("rejected" if scope.endswith("mismatch") else "incomplete", scope, base)
    if scope["recipient_classification"] != "spread_multi_target" or scope["canonical_target_class"] != target_set["canonical_target_class"]:
        return _result("rejected", "wide_guard_target_set_execution_scope_classification_mismatch", base)
    recipients = tuple(row for row in scope["recipients"] if row.get("side") == base["protected_side"])
    if not recipients: return _no(base, context, target_set, "no_incoming_recipient_on_protected_side", scope=scope)
    if tuple(scope["recipients"]) != tuple(target_set["recipients"]) or not _recipients(recipients, base["protected_side"]): return _result("rejected", "wide_guard_protected_recipient_identity_conflict", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": "applies", "protected_recipients": deepcopy(recipients), "incoming_recipient_classification": scope["recipient_classification"], "target_set_authority": deepcopy(dict(target_set_authority)), "execution_scope_authority": deepcopy(dict(execution_scope_authority)), "protection_context": context, "provenance": "runtime_d0_canonical_wide_guard_frozen_spread_applicability_v1"}


def _base(d0: Any, guard: Any, guard_action: Any, incoming: Any, protected_side: Any, decision_point: Any) -> dict[str, Any] | None:
    try: guard_owner = _owner(guard)
    except ValueError: return None
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(guard_action, str) or not guard_action or not isinstance(incoming, Mapping) or protected_side not in {"self", "opponent"} or protected_side != guard_owner["side"] or not isinstance(decision_point, str) or not decision_point:
        return None
    actor = d0.get("decision_owner")
    if not _owner_value(actor) or d0.get("active_owners", {}).get(guard_owner["side"]) != guard_owner or incoming.get("action_id") is None or not isinstance(incoming.get("action_id"), str) or not isinstance(incoming.get("identity"), str) or actor != d0.get("active_owners", {}).get(actor.get("side")):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(actor)), "decision_point": decision_point, "guard_user": guard_owner, "guard_action_id": guard_action, "guard_move_id": "wide-guard", "incoming_actor": deepcopy(dict(actor)), "incoming_action_id": incoming["action_id"], "incoming_move_id": incoming["identity"], "protected_side": protected_side}


def _context(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, Mapping): return None
    try: expected = build_wide_guard_protection_context(session_id=base["session_id"], guard_user=base["guard_user"], guard_action_id=base["guard_action_id"], incoming_actor=base["incoming_actor"], incoming_action_id=base["incoming_action_id"], incoming_move_id=base["incoming_move_id"], protected_side=base["protected_side"], protection_authority=value.get("protection_authority"), action_blocked=value.get("action_blocked"), protection_bypass=value.get("protection_bypass"))
    except (TypeError, ValueError): return None
    return expected if value == expected else None
def _target_set(value: Any, base: Mapping[str, Any]) -> Mapping[str, Any] | str:
    if not isinstance(value, Mapping): return "wide_guard_target_set_authority_missing"
    if value.get("status") != "resolved" or value.get("schema_version") != TARGET_SET_SCHEMA: return "wide_guard_target_set_authority_unavailable"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "acting_owner", "action_id", "move_id", "decision_point")
    expected = {**base, "acting_owner": base["incoming_actor"], "action_id": base["incoming_action_id"], "move_id": base["incoming_move_id"]}
    return value if all(value.get(key) == expected[key] for key in keys) else "wide_guard_target_set_authority_binding_mismatch"
def _scope(value: Any, base: Mapping[str, Any], target_set: Mapping[str, Any]) -> Mapping[str, Any] | str:
    if not isinstance(value, Mapping): return "wide_guard_execution_scope_authority_missing"
    if value.get("status") != "resolved" or value.get("schema_version") != SCOPE_SCHEMA: return "wide_guard_execution_scope_authority_unavailable"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "acting_owner", "action_id", "move_id", "decision_point")
    expected = {**base, "acting_owner": base["incoming_actor"], "action_id": base["incoming_action_id"], "move_id": base["incoming_move_id"]}
    if any(value.get(key) != expected[key] for key in keys) or value.get("target_set_authority") != target_set: return "wide_guard_execution_scope_authority_binding_mismatch"
    return value
def _recipients(value: tuple[Any, ...], side: str) -> bool:
    identities = set()
    for row in value:
        owner = row.get("owner") if isinstance(row, Mapping) else None
        key = (owner.get("session_id"), owner.get("side"), owner.get("slot_index"), owner.get("pokemon_id")) if isinstance(owner, Mapping) else None
        if not isinstance(row, Mapping) or row.get("side") != side or row.get("relation") != "opponent" or row.get("selected") is not False or not _owner_value(owner) or owner.get("side") != side or owner.get("slot_index") != row.get("active_slot_index") or key in identities: return False
        identities.add(key)
    return True
def _protection(value: Any, owner: Mapping[str, Any]) -> bool: return isinstance(value, Mapping) and value.get("status") == "resolved" and value.get("owner") == owner and isinstance(value.get("metadata"), Mapping) and value["metadata"].get("move_id") == "wide-guard"
def _owner(value: Any) -> dict[str, Any]:
    if not _owner_value(value): raise ValueError("invalid_wide_guard_owner")
    return deepcopy(dict(value))
def _owner_value(value: Any) -> bool: return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value["slot_index"], bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
def _no(base: Mapping[str, Any], context: Mapping[str, Any], target_set: Mapping[str, Any], reason: str, *, scope: Mapping[str, Any] | None = None) -> dict[str, Any]: return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "reason": reason, "protected_recipients": (), "incoming_recipient_classification": target_set.get("recipient_classification"), "target_set_authority": deepcopy(dict(target_set)), **({"execution_scope_authority": deepcopy(dict(scope))} if scope else {}), "protection_context": deepcopy(dict(context)), "provenance": "runtime_d0_canonical_wide_guard_no_effect_v1"}
def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
