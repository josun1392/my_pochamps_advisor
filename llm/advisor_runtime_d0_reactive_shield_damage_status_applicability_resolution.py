"""Strict adapter from common reactive-shield facts to existing lower inputs."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from advisor.canonical_baneful_bunker_reactive_poison import canonical_baneful_bunker_reactive_poison_metadata
from advisor.canonical_burning_bulwark_reactive_burn import canonical_burning_bulwark_reactive_burn_metadata
from advisor.canonical_spiky_shield_reactive_damage import canonical_spiky_shield_reactive_damage_metadata
from llm.advisor_runtime_d0_baneful_bunker_reactive_poison_authority import (
    build_baneful_bunker_reactive_poison_applicability_resolution,
    build_baneful_bunker_successful_block_context,
)
from llm.advisor_runtime_d0_burning_bulwark_reactive_burn_authority import (
    build_burning_bulwark_reactive_burn_applicability_resolution,
    build_burning_bulwark_successful_block_context,
)
from llm.advisor_runtime_d0_reactive_shield_common_block_context import SCHEMA_VERSION as COMMON_SCHEMA
from llm.advisor_runtime_d0_spiky_shield_reactive_damage_authority import (
    build_spiky_shield_reactive_damage_applicability_resolution,
    build_spiky_shield_successful_block_context,
)
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
from llm.advisor_substitute import substitute_state


SCHEMA_VERSION = "runtime-d0-reactive-shield-damage-status-applicability-resolution-v1"
_FAMILIES: dict[str, tuple[str, Callable[[Any], Mapping[str, Any] | None], Callable[..., dict[str, Any]], Callable[..., dict[str, Any]], frozenset[str]]] = {
    "spiky_shield": ("spiky-shield", canonical_spiky_shield_reactive_damage_metadata, build_spiky_shield_successful_block_context, build_spiky_shield_reactive_damage_applicability_resolution, frozenset({"magic-guard"})),
    "baneful_bunker": ("baneful-bunker", canonical_baneful_bunker_reactive_poison_metadata, build_baneful_bunker_successful_block_context, build_baneful_bunker_reactive_poison_applicability_resolution, frozenset({"immunity"})),
    "burning_bulwark": ("burning-bulwark", canonical_burning_bulwark_reactive_burn_metadata, build_burning_bulwark_successful_block_context, build_burning_bulwark_reactive_burn_applicability_resolution, frozenset({"water-veil"})),
}
_NEUTRAL_ABILITIES = frozenset({"pressure"})


def freeze_runtime_d0_reactive_shield_damage_status_applicability_resolution(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], common_block_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Adapt exact common facts without inventing a shield block or modifier result."""
    base = _base(strategy_d0, common_block_context)
    if base is None:
        return _result("rejected", "reactive_shield_damage_status_common_context_binding_invalid", {})
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)
    if common_block_context.get("status") != "resolved":
        return _result(_status(common_block_context), common_block_context.get("reason", "reactive_shield_common_context_unavailable"), base)
    outcome = common_block_context.get("outcome")
    if outcome == "protection_not_applicable":
        if not _valid_bypass(common_block_context.get("bypass_authority"), base):
            return _result("rejected", "reactive_shield_damage_status_bypass_binding_invalid", base)
        return _resolved_not_applicable(base, "common_protection_not_applicable")
    if outcome == "protection_applies_non_contact":
        if not _common_facts_match(common_block_context, base, "non_contact"):
            return _result("rejected", "reactive_shield_damage_status_common_facts_invalid", base)
        return _resolved_not_applicable(base, "common_protection_applies_non_contact")
    if outcome != "protection_applies_contact" or not _common_facts_match(common_block_context, base, "contact"):
        return _result("rejected", "reactive_shield_damage_status_common_facts_invalid", base)
    substitute = _substitute_authority(strategy_d0, base["blocked_attacker"])
    if substitute.get("status") != "known_absent":
        return _result("incomplete", substitute.get("reason", "reactive_shield_substitute_state_unavailable"), base, substitute_authority=substitute)
    modifiers = _current_modifier_authorities(runtime_snapshot, base["blocked_attacker"])
    if modifiers is None:
        return _result("incomplete", "reactive_shield_target_modifier_authority_unknown", base)
    applicability = _applicability(strategy_d0, runtime_snapshot, base, modifiers)
    if applicability.get("status") != "resolved":
        return _result(_status(applicability), applicability.get("reason", "reactive_shield_modifier_applicability_unavailable"), base, substitute_authority=substitute)
    family = _FAMILIES[base["shield_family"]]
    protection = {
        "status": "resolved", "owner": deepcopy(dict(base["shield_owner"])),
        "metadata": {"move_id": family[0]},
        "provenance": "derived_from_runtime_d0_reactive_shield_common_block_context_v1",
    }
    try:
        block = family[2](
            session_id=base["session_id"], shield_owner=base["shield_owner"], shield_action_id=base["shield_action_id"],
            blocked_attacker=base["blocked_attacker"], blocked_action_id=base["blocked_action_id"], blocked_move_id=base["blocked_move_id"],
            protection_authority=protection, action_blocked=True, protection_bypass=False, substitute_authority=substitute,
        )
        resolution = family[3](
            session_id=base["session_id"], shield_owner=base["shield_owner"], blocked_attacker=base["blocked_attacker"],
            blocked_action_id=base["blocked_action_id"], blocked_move_id=base["blocked_move_id"], outcome=applicability["outcome"],
            ability_authority=modifiers["ability_authority"], item_authority=modifiers["item_authority"],
        )
    except (TypeError, ValueError):
        return _result("rejected", "reactive_shield_damage_status_legacy_adapter_invalid", base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base, "outcome": applicability["outcome"],
        "contact_authority": deepcopy(dict(common_block_context["contact_authority"])),
        "protection_success_authority": deepcopy(dict(common_block_context["protection_success_authority"])),
        "bypass_authority": deepcopy(dict(common_block_context["bypass_authority"])),
        "substitute_authority": substitute, "protection_block_context": block,
        "applicability_resolution": resolution, "modifier_applicability": applicability,
        "provenance": "runtime_d0_reactive_shield_damage_status_legacy_input_adapter_v1",
    }


def _base(d0: Any, context: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not isinstance(context, Mapping) or context.get("schema_version") != COMMON_SCHEMA:
        return None
    family = context.get("shield_family")
    if family not in _FAMILIES:
        return None
    move_id, resolver, *_ = _FAMILIES[family]
    required = {"session_id": d0.get("session_id"), "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"), "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"), "decision_owner": d0.get("decision_owner")}
    if any(context.get(key) != value for key, value in required.items()) or context.get("shield_move_id") != move_id or resolver(move_id) is None:
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get("opponent") != context.get("shield_owner") or active.get("self") != context.get("blocked_attacker"):
        return None
    if not all(isinstance(context.get(key), str) and context[key] for key in ("shield_action_id", "blocked_action_id", "blocked_move_id")):
        return None
    return {**{key: deepcopy(value) if isinstance(value, Mapping) else value for key, value in required.items()}, "shield_owner": deepcopy(dict(context["shield_owner"])), "shield_action_id": context["shield_action_id"], "shield_move_id": move_id, "shield_family": family, "blocked_attacker": deepcopy(dict(context["blocked_attacker"])), "blocked_action_id": context["blocked_action_id"], "blocked_move_id": context["blocked_move_id"]}


def _common_facts_match(context: Mapping[str, Any], base: Mapping[str, Any], contact_state: str) -> bool:
    success = context.get("protection_success_authority")
    contact = context.get("contact_authority")
    return isinstance(success, Mapping) and success.get("schema_version") == "branch-protection-success-v1" and success.get("owner") == base["shield_owner"] and success.get("previous_successful_protection_count") == 0 and success.get("provenance") == "explicit_branch_nonconsecutive_protection" and _valid_bypass(context.get("bypass_authority"), base, expected=False) and isinstance(contact, Mapping) and contact.get("status") == "resolved" and contact.get("contact_state") == contact_state and all(contact.get(key) == base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) and contact.get("action_id") == base["blocked_action_id"] and contact.get("move_id") == base["blocked_move_id"] and contact.get("attacker") == base["blocked_attacker"] and contact.get("target") == base["shield_owner"]


def _valid_bypass(value: Any, base: Mapping[str, Any], *, expected: bool | None = None) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "resolved" and isinstance(value.get("bypassed"), bool) and (expected is None or value.get("bypassed") is expected) and all(value.get(key) == base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) and value.get("blocked_attacker") == base["blocked_attacker"] and value.get("blocked_action_id") == base["blocked_action_id"] and value.get("blocked_move_id") == base["blocked_move_id"]


def _substitute_authority(d0: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    state = substitute_state(d0.get("strategy_state", {}), owner)
    if state.get("state") == "known_inactive":
        return {"status": "known_absent"}
    if state.get("state") == "known_active":
        return {"status": "incomplete", "reason": "reactive_shield_active_substitute_semantics_unsupported"}
    return {"status": "incomplete", "reason": "reactive_shield_substitute_state_untracked"}


def _current_modifier_authorities(snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    state = snapshot.get("state") if isinstance(snapshot, Mapping) else None
    side = state.get(f"{owner.get('side')}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(row, Mapping) or row.get("pokemon_id") != owner.get("pokemon_id"):
        return None
    ability, ability_provenance = row.get("current_ability"), row.get("current_ability_provenance")
    item, item_provenance = row.get("known_item"), row.get("known_item_provenance")
    if not isinstance(ability, str) or not ability or not _trusted(ability_provenance, "current_ability_observed") or not _trusted(item_provenance, "current_item_observed"):
        return None
    if item is None and item_provenance.get("status") == "known_absent":
        item_authority = {"status": "known_absent"}
    elif isinstance(item, str) and item and item_provenance.get("status") == "known":
        item_authority = {"status": "known", "value": item}
    else:
        return None
    return {"ability_authority": {"status": "known", "value": ability}, "item_authority": item_authority}


def _applicability(d0: Mapping[str, Any], snapshot: Mapping[str, Any], base: Mapping[str, Any], modifiers: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ability = modifiers["ability_authority"].get("value")
    item = modifiers["item_authority"]
    if item.get("status") != "known_absent":
        return _result("incomplete", "reactive_shield_item_interaction_unmaintained", base)
    if ability in _NEUTRAL_ABILITIES:
        return {"status": "resolved", "outcome": "applies", "reason": "maintained_neutral_modifier", "ability_authority": deepcopy(dict(modifiers["ability_authority"])), "item_authority": deepcopy(dict(item))}
    if ability not in _FAMILIES[base["shield_family"]][4]:
        return _result("incomplete", "reactive_shield_ability_interaction_unmaintained", base)
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or set(active) != {"self", "opponent"}:
        return _result("rejected", "reactive_shield_modifier_suppression_active_owners_invalid", base)
    abilities = {side: _current_modifier_authorities(snapshot, owner) for side, owner in active.items()}
    if any(value is None for value in abilities.values()):
        return _result("incomplete", "reactive_shield_modifier_suppression_unknown", base)
    suppressed = any(value["ability_authority"].get("value") == "neutralizing-gas" for value in abilities.values())
    return {"status": "resolved", "outcome": "applies" if suppressed else "prevented", "reason": "prevention_ability_suppressed" if suppressed else "maintained_prevention_ability", "ability_authority": deepcopy(dict(modifiers["ability_authority"])), "item_authority": deepcopy(dict(item)), "suppression_authorities": deepcopy(abilities)}


def _resolved_not_applicable(base: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "outcome": "not_applicable", "reason": reason, "provenance": "runtime_d0_reactive_shield_damage_status_legacy_input_adapter_v1"}


def _trusted(value: Any, event_kind: str) -> bool:
    return isinstance(value, Mapping) and value.get("event_kind") == event_kind and value.get("trust") == "user_confirmed_observation"


def _status(value: Any) -> str:
    return value.get("status") if isinstance(value, Mapping) and value.get("status") in {"incomplete", "rejected"} else "rejected"


def _result(status: str, reason: str, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
