"""Strict common live facts for a blocked action against a reactive shield."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_silk_trap_reactive_protection import canonical_silk_trap_metadata, canonical_kings_shield_metadata, canonical_obstruct_metadata
from advisor.canonical_spiky_shield_reactive_damage import canonical_spiky_shield_reactive_damage_metadata
from advisor.canonical_baneful_bunker_reactive_poison import canonical_baneful_bunker_reactive_poison_metadata
from advisor.canonical_burning_bulwark_reactive_burn import canonical_burning_bulwark_reactive_burn_metadata
from llm.advisor_runtime_d0_canonical_contact_classification_authority import freeze_runtime_d0_canonical_contact_classification_authority
from llm.advisor_runtime_d0_nonconsecutive_protection_success_authority import freeze_runtime_d0_nonconsecutive_protection_success_authority
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-reactive-shield-common-block-context-v1"


def freeze_runtime_d0_reactive_shield_common_block_context(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], shield_owner: Mapping[str, Any], shield_action: Mapping[str, Any], blocked_attacker: Mapping[str, Any], blocked_action: Mapping[str, Any], frozen_move_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve only shield success, bypass, and contact; never a family consequence."""
    base = _base(strategy_d0, shield_owner, shield_action, blocked_attacker, blocked_action, frozen_move_metadata)
    if base is None:
        return _result("rejected", "invalid_reactive_shield_common_block_request", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    bypassed = frozen_move_metadata.get("protection_bypass")
    if not isinstance(bypassed, bool):
        return _result("incomplete", "reactive_shield_protection_bypass_unknown", base)
    bypass = {"status": "resolved", "schema_version": "runtime-d0-reactive-shield-incoming-bypass-authority-v1", "session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "decision_owner": deepcopy(base["decision_owner"]), "blocked_attacker": deepcopy(base["blocked_attacker"]), "blocked_action_id": base["blocked_action_id"], "blocked_move_id": base["blocked_move_id"], "bypassed": bypassed, "provenance": "frozen_selectable_own_action_protection_bypass_v1"}
    if bypassed:
        return _resolved("protection_not_applicable", "incoming_action_explicitly_bypasses_protection", base, None, None, bypass)
    if frozen_move_metadata.get("category") not in {"physical", "special"}:
        return _resolved("protection_not_applicable", "incoming_action_not_supported_direct_damage", base, None, None, bypass)
    protection = freeze_runtime_d0_nonconsecutive_protection_success_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        protection_owner=shield_owner, protection_action=shield_action,
    )
    if protection.get("status") != "resolved":
        return _result(_status(protection), protection.get("reason", "reactive_shield_protection_success_unavailable"), base, protection_success_source=protection, bypass_authority=bypass)
    success = protection.get("protection_success_authority")
    if not isinstance(success, Mapping):
        return _result("rejected", "reactive_shield_protection_success_payload_invalid", base, protection_success_source=protection, bypass_authority=bypass)
    contact = freeze_runtime_d0_canonical_contact_classification_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, action=blocked_action,
        attacker=blocked_attacker, target=shield_owner,
    )
    if contact.get("status") != "resolved":
        return _result(_status(contact), contact.get("reason", "reactive_shield_contact_authority_unavailable"), base, protection_success_authority=success, contact_authority=contact, bypass_authority=bypass)
    contact_state = contact.get("contact_state")
    if contact_state not in {"contact", "non_contact"}:
        return _result("rejected", "reactive_shield_contact_state_invalid", base, protection_success_authority=success, contact_authority=contact, bypass_authority=bypass)
    return _resolved(f"protection_applies_{contact_state}", "reactive_shield_common_facts_resolved", base, success, contact, bypass)


def _base(d0: Any, shield: Any, shield_action: Any, attacker: Any, action: Any, metadata: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not all(isinstance(value, Mapping) for value in (shield, shield_action, attacker, action, metadata)):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get("opponent") != dict(shield) or active.get("self") != dict(attacker) or d0.get("decision_owner") != dict(attacker):
        return None
    shield_move_id = shield_action.get("move_id", shield_action.get("identity"))
    family = _family(shield_move_id)
    shield_metadata = shield_action.get("metadata_authority", {}).get("metadata") if isinstance(shield_action.get("metadata_authority"), Mapping) else None
    if family is None or shield_action.get("action_type") != "attack" or not isinstance(shield_action.get("action_id"), str) or not shield_action["action_id"] or not isinstance(shield_metadata, Mapping) or shield_metadata.get("move_id") != shield_move_id:
        return None
    if not isinstance(action.get("action_id"), str) or not action["action_id"] or not isinstance(action.get("identity"), str) or not action["identity"] or metadata.get("move_id") != action["identity"]:
        return None
    if any(not isinstance(d0.get(key), str) or not d0[key] for key in ("session_id", "source_runtime_fingerprint", "strategy_preview_fingerprint")):
        return None
    return {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0.get("decision_owner")), "shield_owner": deepcopy(dict(shield)), "shield_action_id": shield_action["action_id"], "shield_move_id": shield_move_id, "shield_family": family, "blocked_attacker": deepcopy(dict(attacker)), "blocked_action_id": action["action_id"], "blocked_move_id": action["identity"], "protection_bypass": metadata.get("protection_bypass")}


def _family(move_id: Any) -> str | None:
    for family, resolver in (("silk_trap", canonical_silk_trap_metadata), ("kings_shield", canonical_kings_shield_metadata), ("obstruct", canonical_obstruct_metadata), ("spiky_shield", canonical_spiky_shield_reactive_damage_metadata), ("baneful_bunker", canonical_baneful_bunker_reactive_poison_metadata), ("burning_bulwark", canonical_burning_bulwark_reactive_burn_metadata)):
        if resolver(move_id) is not None:
            return family
    return None


def _resolved(outcome: str, reason: str, base: Mapping[str, Any], success: Mapping[str, Any] | None, contact: Mapping[str, Any] | None, bypass: Mapping[str, Any]) -> dict[str, Any]:
    result = {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": outcome, "provenance": "runtime_d0_reactive_shield_common_block_facts_v1", "reason": reason}
    result["bypass_authority"] = deepcopy(dict(bypass))
    if success is not None: result["protection_success_authority"] = deepcopy(dict(success))
    if contact is not None: result["contact_authority"] = deepcopy(dict(contact))
    return result


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "rejected", "unsupported"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
