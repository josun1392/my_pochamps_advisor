"""Strict Mat Block applicability; consumers never infer its coverage."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_mat_block_protection import canonical_mat_block_protection_metadata
from llm.advisor_runtime_d0_mat_block_active_entry_eligibility_authority import SCHEMA_VERSION as ELIGIBILITY_SCHEMA

SCHEMA_VERSION = "runtime-d0-mat-block-direct-damage-applicability-authority-v1"
BYPASS_SCHEMA_VERSION = "runtime-d0-mat-block-incoming-bypass-authority-v1"

def freeze_runtime_d0_mat_block_incoming_bypass_authority(*, strategy_d0: Mapping[str, Any], incoming_actor: Mapping[str, Any], incoming_action: Mapping[str, Any], frozen_move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the canonical bypass fact from the already-frozen selected action."""
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved": return _bypass_result("rejected", "invalid_runtime_d0", {})
    if not isinstance(incoming_actor, Mapping) or not isinstance(incoming_action, Mapping) or not isinstance(frozen_move_metadata, Mapping): return _bypass_result("rejected", "mat_block_bypass_input_malformed", {})
    active_owners = strategy_d0.get("active_owners")
    if not isinstance(active_owners, Mapping) or active_owners.get("self") != dict(incoming_actor): return _bypass_result("rejected", "mat_block_bypass_incoming_actor_mismatch", {})
    action_id, move_id = incoming_action.get("action_id"), incoming_action.get("identity")
    if not isinstance(action_id, str) or not action_id or not isinstance(move_id, str) or not move_id or frozen_move_metadata.get("move_id") != move_id: return _bypass_result("rejected", "mat_block_bypass_action_metadata_mismatch", {})
    bypassed = frozen_move_metadata.get("protection_bypass")
    base = {"session_id": strategy_d0.get("session_id"), "source_runtime_fingerprint": strategy_d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": strategy_d0.get("strategy_preview_fingerprint"), "decision_owner": deepcopy(strategy_d0.get("decision_owner")), "incoming_actor": deepcopy(dict(incoming_actor)), "incoming_action_id": action_id, "incoming_move_id": move_id}
    if not all(isinstance(base.get(key), str) and base[key] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")): return _bypass_result("rejected", "mat_block_bypass_runtime_binding_invalid", base)
    if not isinstance(bypassed, bool): return _bypass_result("incomplete", "mat_block_bypass_unknown", base)
    return {"status": "resolved", "schema_version": BYPASS_SCHEMA_VERSION, **base, "bypassed": bypassed, "provenance": "frozen_selectable_own_action_protection_bypass_v1"}


def freeze_runtime_d0_mat_block_direct_damage_applicability_authority(*, eligibility_authority: Mapping[str, Any] | None, bypass_authority: Mapping[str, Any] | None, incoming_action: Mapping[str, Any], protected_recipients: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    """Freeze the exact direct-damage applicability result from strict inputs."""
    base = _base(eligibility_authority, incoming_action, protected_recipients)
    if base is None: return _result("rejected", "mat_block_request_binding_invalid", {})
    if eligibility_authority is None: return _result("incomplete", "mat_block_active_entry_eligibility_missing", base)
    if eligibility_authority.get("schema_version") != ELIGIBILITY_SCHEMA or eligibility_authority.get("status") != "resolved": return _result(eligibility_authority.get("status", "rejected") if isinstance(eligibility_authority, Mapping) else "incomplete", eligibility_authority.get("reason", "mat_block_active_entry_eligibility_unavailable") if isinstance(eligibility_authority, Mapping) else "mat_block_active_entry_eligibility_missing", base)
    if eligibility_authority.get("eligibility") == "ineligible": return _resolved("not_applicable", "mat_block_active_entry_ineligible", base, eligibility_authority, None)
    if eligibility_authority.get("eligibility") != "eligible": return _result("rejected", "mat_block_active_entry_eligibility_invalid", base)
    if bypass_authority is None: return _result("incomplete", "mat_block_bypass_authority_missing", base)
    if not isinstance(bypass_authority, Mapping) or not _bypass_matches(bypass_authority, base): return _result("rejected", "mat_block_bypass_authority_binding_mismatch", base)
    if bypass_authority.get("status") != "resolved": return _result("incomplete", "mat_block_bypass_authority_unresolved", base)
    if bypass_authority.get("bypassed") is True: return _resolved("not_applicable", "mat_block_incoming_action_bypasses_guard", base, eligibility_authority, bypass_authority)
    if bypass_authority.get("bypassed") is not False: return _result("rejected", "mat_block_bypass_authority_invalid", base)
    if incoming_action.get("category") not in {"physical", "special"}: return _resolved("not_applicable", "mat_block_incoming_action_not_supported_direct_damage", base, eligibility_authority, bypass_authority)
    return _resolved("applies", "mat_block_exact_direct_damage_protected", base, eligibility_authority, bypass_authority)

def _base(eligibility: Any, incoming: Any, recipients: Any) -> dict[str, Any] | None:
    if not isinstance(eligibility, Mapping) or not isinstance(incoming, Mapping) or not isinstance(recipients, tuple) or not recipients: return None
    if canonical_mat_block_protection_metadata(eligibility.get("mat_block_move_id")) is None: return None
    if not all(isinstance(incoming.get(k), str) and incoming[k] for k in ("action_id", "move_id")) or incoming.get("category") not in {"physical", "special", "status"}: return None
    if any(not isinstance(row, Mapping) or set(row) != {"session_id", "side", "slot_index", "pokemon_id"} for row in recipients) or len({(row["side"], row["slot_index"], row["pokemon_id"]) for row in recipients}) != len(recipients): return None
    if len(recipients) != 1 or dict(recipients[0]) != eligibility.get("mat_block_user"): return None
    return {"session_id": eligibility.get("session_id"), "source_runtime_fingerprint": eligibility.get("source_runtime_fingerprint"), "source_branch_fingerprint": eligibility.get("source_branch_fingerprint"), "decision_owner": deepcopy(eligibility.get("decision_owner")), "mat_block_user": deepcopy(eligibility.get("mat_block_user")), "mat_block_action_id": eligibility.get("mat_block_action_id"), "mat_block_move_id": "mat-block", "active_entry_token": eligibility.get("active_entry_token"), "incoming_action": deepcopy(dict(incoming)), "protected_recipients": tuple(deepcopy(dict(row)) for row in recipients)}


def _bypass_matches(bypass: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    incoming = base.get("incoming_action")
    return bypass.get("schema_version") == BYPASS_SCHEMA_VERSION and bypass.get("session_id") == base.get("session_id") and bypass.get("source_runtime_fingerprint") == base.get("source_runtime_fingerprint") and bypass.get("source_branch_fingerprint") == base.get("source_branch_fingerprint") and bypass.get("decision_owner") == base.get("decision_owner") and bypass.get("incoming_actor") == base.get("decision_owner") and isinstance(incoming, Mapping) and bypass.get("incoming_action_id") == incoming.get("action_id") and bypass.get("incoming_move_id") == incoming.get("move_id")

def _resolved(outcome, reason, base, eligibility, bypass):
    result = {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": outcome, "active_entry_eligibility_authority": deepcopy(dict(eligibility)), "provenance": "strict_mat_block_active_entry_direct_damage_applicability_v1", "reason": reason}
    if bypass is not None: result["bypass_authority"] = deepcopy(dict(bypass))
    return result
def _result(status, reason, base): return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
def _bypass_result(status, reason, base): return {"status": status, "schema_version": BYPASS_SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
