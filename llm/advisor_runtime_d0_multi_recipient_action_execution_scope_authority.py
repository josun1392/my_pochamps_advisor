"""Strict D0 authority for canonical execution scopes of one spread action."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_multi_recipient_action_execution import canonical_multi_recipient_action_execution_metadata
from llm.advisor_runtime_strategy_d0 import resolve_runtime_d0_selectable_move_metadata_authority, runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-multi-recipient-action-execution-scope-authority-v1"
TARGET_SET_SCHEMA = "runtime-d0-doubles-action-target-set-authority-v1"
_SCOPES = frozenset({"action_shared", "recipient_local", "deterministic"})


def freeze_runtime_d0_multi_recipient_action_execution_scope_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], decision_point: str, target_set_authority: Mapping[str, Any]) -> dict[str, Any]:
    base = _base(strategy_d0, action, decision_point)
    if base is None:
        return _result("rejected", "invalid_runtime_d0_or_multi_recipient_execution_scope_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    target_set = _target_set(target_set_authority, base)
    if isinstance(target_set, str):
        return _result("rejected" if target_set.endswith("binding_mismatch") else "incomplete", target_set, base)
    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=strategy_d0, action=action)
    common = {**base, "target_set_authority": deepcopy(dict(target_set_authority)) if isinstance(target_set_authority, Mapping) else None, "move_metadata_authority": deepcopy(metadata_authority)}
    if metadata_authority.get("status") != "resolved":
        return _result("rejected" if metadata_authority.get("status") == "rejected" else "incomplete", metadata_authority.get("reason", "canonical_move_metadata_unavailable"), common)
    metadata = metadata_authority.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != base["move_id"]:
        return _result("rejected", "canonical_move_metadata_binding_conflict", common)
    canonical = canonical_multi_recipient_action_execution_metadata(base["move_id"])
    if canonical is None:
        return _result("incomplete", "canonical_multi_recipient_execution_scope_missing", common)
    if metadata.get("target") != canonical["canonical_target_class"] or metadata.get("category") not in {"physical", "special"} or not isinstance(metadata.get("power"), int) or isinstance(metadata.get("power"), bool) or metadata["power"] < 1:
        return _result("rejected", "canonical_move_metadata_execution_scope_conflict", common)
    if target_set["canonical_target_class"] != canonical["canonical_target_class"] or target_set["recipient_classification"] != canonical["recipient_classification"]:
        return _result("rejected", "target_set_canonical_classification_mismatch", common)
    recipients = target_set["recipients"]
    if not isinstance(recipients, tuple) or len(recipients) < 2 or not _recipients(recipients):
        return _result("rejected", "target_set_recipient_order_invalid", common)
    modifier = canonical["spread_damage_modifier"]
    if not _modifier(modifier) or len(recipients) < modifier["applies_when_recipient_count_at_least"]:
        return _result("incomplete", "canonical_spread_damage_modifier_unavailable", common)
    scopes = {key: canonical.get(key) for key in ("accuracy_uncertainty_scope", "critical_hit_uncertainty_scope", "damage_roll_uncertainty_scope")}
    if any(value not in _SCOPES for value in scopes.values()):
        return _result("incomplete", "canonical_multi_recipient_rng_scope_missing", common)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **common,
        "canonical_target_class": canonical["canonical_target_class"],
        "recipient_classification": canonical["recipient_classification"],
        "recipients": deepcopy(recipients),
        "recipient_resolution_order": canonical["recipient_resolution_order"],
        "spread_damage_modifier_authority": {"status": "resolved", **deepcopy(modifier), "provenance": "canonical_multi_recipient_action_execution_scope_v1"},
        **scopes, "canonical_execution_metadata": canonical,
        "provenance": "runtime_d0_canonical_multi_recipient_action_execution_scope_v1",
    }


def _base(d0: Any, action: Any, decision_point: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(action, Mapping) or not isinstance(decision_point, str) or not decision_point:
        return None
    actor = d0.get("decision_owner")
    if not isinstance(actor, Mapping) or d0.get("active_owners", {}).get(actor.get("side")) != dict(actor) or not isinstance(action.get("action_id"), str) or not action["action_id"] or not isinstance(action.get("identity"), str) or not action["identity"]:
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(actor)), "acting_owner": deepcopy(dict(actor)), "action_id": action["action_id"], "move_id": action["identity"], "decision_point": decision_point}


def _target_set(value: Any, base: Mapping[str, Any]) -> dict[str, Any] | str:
    if not isinstance(value, Mapping): return "doubles_target_set_authority_missing"
    if value.get("status") != "resolved" or value.get("schema_version") != TARGET_SET_SCHEMA:
        return "doubles_target_set_authority_unavailable"
    keys = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "acting_owner", "action_id", "move_id", "decision_point")
    if any(value.get(key) != base[key] for key in keys): return "doubles_target_set_authority_binding_mismatch"
    return deepcopy(dict(value))


def _recipients(value: tuple[Any, ...]) -> bool:
    identities = set()
    previous_slot = -1
    for row in value:
        owner = row.get("owner") if isinstance(row, Mapping) else None
        if not isinstance(row, Mapping) or row.get("relation") != "opponent" or row.get("selected") is not False or row.get("side") != "opponent" or not isinstance(row.get("active_slot_index"), int) or isinstance(row.get("active_slot_index"), bool) or not isinstance(owner, Mapping) or owner.get("side") != row["side"] or owner.get("slot_index") != row["active_slot_index"]:
            return False
        identity = (owner.get("session_id"), owner.get("side"), owner.get("slot_index"), owner.get("pokemon_id"))
        if identity in identities or row["active_slot_index"] <= previous_slot: return False
        identities.add(identity)
        previous_slot = row["active_slot_index"]
    return True


def _modifier(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("numerator") == 3 and value.get("denominator") == 4 and value.get("applies_when_recipient_count_at_least") == 2


def _result(status: str, reason: str, base: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
