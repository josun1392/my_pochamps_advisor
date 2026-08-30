"""Strict Mat Block applicability; consumers never infer its coverage."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_mat_block_protection import canonical_mat_block_protection_metadata
from llm.advisor_runtime_d0_mat_block_active_entry_eligibility_authority import SCHEMA_VERSION as ELIGIBILITY_SCHEMA

SCHEMA_VERSION = "runtime-d0-mat-block-direct-damage-applicability-authority-v1"

def freeze_runtime_d0_mat_block_direct_damage_applicability_authority(*, eligibility_authority: Mapping[str, Any] | None, protection_success_authority: Mapping[str, Any] | None, bypass_authority: Mapping[str, Any] | None, incoming_action: Mapping[str, Any], protected_recipients: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    """Freeze the exact direct-damage applicability result from strict inputs."""
    base = _base(eligibility_authority, incoming_action, protected_recipients)
    if base is None: return _result("rejected", "mat_block_request_binding_invalid", {})
    if eligibility_authority is None: return _result("incomplete", "mat_block_active_entry_eligibility_missing", base)
    if eligibility_authority.get("schema_version") != ELIGIBILITY_SCHEMA or eligibility_authority.get("status") != "resolved": return _result(eligibility_authority.get("status", "rejected") if isinstance(eligibility_authority, Mapping) else "incomplete", eligibility_authority.get("reason", "mat_block_active_entry_eligibility_unavailable") if isinstance(eligibility_authority, Mapping) else "mat_block_active_entry_eligibility_missing", base)
    if protection_success_authority is None or bypass_authority is None: return _result("incomplete", "mat_block_protection_success_or_bypass_missing", base)
    if not isinstance(protection_success_authority, Mapping) or not isinstance(bypass_authority, Mapping): return _result("rejected", "mat_block_protection_context_malformed", base)
    if eligibility_authority.get("eligibility") == "ineligible": return _resolved("not_applicable", "mat_block_active_entry_ineligible", base, eligibility_authority, protection_success_authority, bypass_authority)
    if eligibility_authority.get("eligibility") != "eligible": return _result("rejected", "mat_block_active_entry_eligibility_invalid", base)
    if protection_success_authority.get("status") != "resolved" or bypass_authority.get("status") != "resolved": return _result("incomplete", "mat_block_protection_context_unresolved", base)
    if protection_success_authority.get("success") is False or bypass_authority.get("bypassed") is True: return _resolved("not_applicable", "mat_block_protection_failed_or_bypassed", base, eligibility_authority, protection_success_authority, bypass_authority)
    if protection_success_authority.get("success") is not True or bypass_authority.get("bypassed") is not False: return _result("rejected", "mat_block_protection_context_invalid", base)
    if incoming_action.get("category") not in {"physical", "special"}: return _resolved("not_applicable", "mat_block_incoming_action_not_supported_direct_damage", base, eligibility_authority, protection_success_authority, bypass_authority)
    return _resolved("applies", "mat_block_exact_direct_damage_protected", base, eligibility_authority, protection_success_authority, bypass_authority)

def _base(eligibility: Any, incoming: Any, recipients: Any) -> dict[str, Any] | None:
    if not isinstance(eligibility, Mapping) or not isinstance(incoming, Mapping) or not isinstance(recipients, tuple) or not recipients: return None
    if canonical_mat_block_protection_metadata(eligibility.get("mat_block_move_id")) is None: return None
    if not all(isinstance(incoming.get(k), str) and incoming[k] for k in ("action_id", "move_id")) or incoming.get("category") not in {"physical", "special", "status"}: return None
    if any(not isinstance(row, Mapping) or set(row) != {"session_id", "side", "slot_index", "pokemon_id"} for row in recipients) or len({(row["side"], row["slot_index"], row["pokemon_id"]) for row in recipients}) != len(recipients): return None
    return {"session_id": eligibility.get("session_id"), "source_runtime_fingerprint": eligibility.get("source_runtime_fingerprint"), "source_branch_fingerprint": eligibility.get("source_branch_fingerprint"), "decision_owner": deepcopy(eligibility.get("decision_owner")), "mat_block_user": deepcopy(eligibility.get("mat_block_user")), "mat_block_action_id": eligibility.get("mat_block_action_id"), "mat_block_move_id": "mat-block", "active_entry_token": eligibility.get("active_entry_token"), "incoming_action": deepcopy(dict(incoming)), "protected_recipients": tuple(deepcopy(dict(row)) for row in recipients)}

def _resolved(outcome, reason, base, eligibility, success, bypass):
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": outcome, "active_entry_eligibility_authority": deepcopy(dict(eligibility)), "protection_success_authority": deepcopy(dict(success)), "bypass_authority": deepcopy(dict(bypass)), "provenance": "strict_mat_block_active_entry_direct_damage_applicability_v1", "reason": reason}
def _result(status, reason, base): return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason}
