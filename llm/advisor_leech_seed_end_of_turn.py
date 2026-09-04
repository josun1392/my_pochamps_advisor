"""Atomic detached Leech Seed tier-eight residual authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ice_body_end_of_turn import _ability, _owners, _sync_hp
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item
from llm.advisor_transition_preview import fingerprint_transition_preview_state

_PROVENANCE = "trusted_leech_seed_persistent_effect_state"


def leech_seed_state(state: Mapping[str, Any], side: str, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    context = state.get("leech_seed_persistent_effect_context")
    if not isinstance(context, Mapping) or context.get("schema_version") != "detached-leech-seed-persistent-effect-v1" or context.get("provenance") != _PROVENANCE or context.get("session_id") != owner.get("session_id") or not isinstance(context.get("source_branch_fingerprint"), str): return None
    rows = context.get("states")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("owner") == dict(owner)] if isinstance(rows, list) else []
    if len(matches) != 1 or matches[0].get("state") not in {"known_active", "known_inactive", "unknown"}: return None
    source_slot = matches[0].get("source_slot")
    if matches[0]["state"] == "known_active" and (not isinstance(source_slot, Mapping) or set(source_slot) != {"session_id", "side", "slot_index"} or source_slot.get("session_id") != owner.get("session_id") or source_slot.get("side") not in {"self", "opponent"} or not isinstance(source_slot.get("slot_index"), int) or isinstance(source_slot.get("slot_index"), bool)): return None
    return matches[0]


def apply_owner_leech_seed_end_of_turn(*, state: dict[str, Any], side: str, owner: Mapping[str, Any], source_branch_fingerprint: str) -> dict[str, Any]:
    owners = _owners(state)
    if owners is None or owners.get(side) != dict(owner) or fingerprint_transition_preview_state(state) != source_branch_fingerprint: return _result("rejected", "stale_or_foreign_leech_seed_owner")
    seed = leech_seed_state(state, side, owner)
    if seed is None: return _result("rejected", "stale_or_invalid_leech_seed_authority")
    if seed["state"] == "unknown": return _result("incomplete", "leech_seed_persistent_effect_unknown")
    if seed["state"] == "known_inactive": return {"status": "resolved", "trace": None}
    if seed["source_slot"]["side"] == side:
        return _result("rejected", "invalid_leech_seed_source_slot_recipient")
    recipient_side = next((candidate for candidate, current in owners.items() if current["session_id"] == seed["source_slot"]["session_id"] and current["side"] == seed["source_slot"]["side"] and current["slot_index"] == seed["source_slot"]["slot_index"]), None)
    if recipient_side is None:
        return {"status": "resolved", "trace": {"effect": "leech_seed", "owner": deepcopy(dict(owner)), "source_slot": deepcopy(dict(seed["source_slot"])), "execution_status": "skipped", "reason": "source_slot_recipient_absent", "provenance": "detached_branch_leech_seed_v1"}}
    target, recipient = state["active"][side], state["active"][recipient_side]
    if target["fainted"]: return _result("rejected", "leech_seed_fainted_seeded_owner")
    if any(not isinstance(active.get(key), int) or isinstance(active.get(key), bool) for active in (target, recipient) for key in ("current_hp", "max_hp")): return _result("incomplete", "leech_seed_current_hp_authority")
    if not 0 < target["current_hp"] <= target["max_hp"] or not 0 <= recipient["current_hp"] <= recipient["max_hp"]: return _result("incomplete", "leech_seed_current_hp_authority")
    recipient_item, target_ability = _item(state, recipient_side), _ability(state, side)
    if recipient_item is _UNKNOWN: return _result("incomplete", "leech_seed_recipient_item_authority")
    if target_ability is None: return _result("incomplete", "leech_seed_target_ability_authority")
    nominal_drain = max(1, target["max_hp"] // 8)
    target_pre, recipient_pre = target["current_hp"], recipient["current_hp"]
    target_ability_name = target_ability
    target_post = target_pre if target_ability_name == "magic-guard" else max(0, target_pre - nominal_drain)
    actual_drain = target_pre - target_post
    attempted_heal = (actual_drain * 5324) // 4096 if recipient_item == "big-root" else actual_drain
    liquid_ooze = target_ability == "liquid-ooze"
    recipient_post = recipient_pre if recipient["fainted"] else (max(0, recipient_pre - attempted_heal) if liquid_ooze else min(recipient["max_hp"], recipient_pre + attempted_heal))
    target["current_hp"], target["fainted"] = target_post, target_post == 0
    recipient["current_hp"], recipient["fainted"] = recipient_post, recipient_post == 0
    _sync_hp(state, side, target_post, target["max_hp"]); _sync_hp(state, recipient_side, recipient_post, recipient["max_hp"])
    return {"status": "resolved", "trace": {"effect": "leech_seed", "owner": deepcopy(dict(owner)), "recipient": deepcopy(owners[recipient_side]), "source_slot": deepcopy(dict(seed["source_slot"])), "target_pre_hp": target_pre, "target_post_hp": target_post, "target_damage": actual_drain, "nominal_drain": nominal_drain, "transfer_basis": actual_drain, "recipient_pre_hp": recipient_pre, "recipient_post_hp": recipient_post, "recipient_modifier": "big_root" if recipient_item == "big-root" else "none", "liquid_ooze": liquid_ooze, "target_ability": target_ability_name, "recipient_item": recipient_item, "attempted_recovery": attempted_heal, "recipient_outcome": "prevented_by_magic_guard" if target_ability_name == "magic-guard" else ("recipient_fainted" if recipient["fainted"] else ("liquid_ooze_damage" if liquid_ooze else "recovered")), "execution_status": "executed", "provenance": "detached_branch_leech_seed_v1"}}


def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "reason": reason}
