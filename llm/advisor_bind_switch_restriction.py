"""Exact Bind-only voluntary-switch restriction on a current detached branch."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Sequence
from llm.advisor_bind_residual import bind_state
from llm.advisor_ice_body_end_of_turn import _owners
from llm.advisor_shadow_tag_switch_block import finalize_switch_candidates
from llm.advisor_switch_permission import normalize_switch_permission_context
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item, _types
from llm.advisor_transition_preview import fingerprint_transition_preview_state

def derive_bind_manual_switch_block(*, branch_state: Mapping[str, Any], source_branch_fingerprint: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    owners = _owners(branch_state)
    if owners is None or fingerprint_transition_preview_state(branch_state) != source_branch_fingerprint or owners.get("self") != dict(owner): return _result("rejected", "stale_or_foreign_bind_switch_authority")
    state = bind_state(branch_state, owner)
    if state["state"] == "legacy_untracked" or state["state"] == "known_inactive": return _resolved(owner, source_branch_fingerprint, state["state"], "not_established")
    if state["state"] == "unknown": return _result("incomplete", "bind_state_unknown")
    # `partiallytrapped.onTrapPokemon` calls tryTrap only while the exact source remains active.
    source = state["source_owner"]
    if owners.get(source["side"]) != source or branch_state["active"][source["side"]].get("fainted"): return _resolved(owner, source_branch_fingerprint, "known_inactive", "not_established")
    types = _types(branch_state, "self")
    if types is None: return _result("incomplete", "bind_switch_current_type_authority")
    if "ghost" in types: return _resolved(owner, source_branch_fingerprint, "known_active", "exception_applies")
    item = _item(branch_state, "self")
    if item is _UNKNOWN: return _result("incomplete", "bind_switch_current_item_authority")
    if item == "shed-shell": return _resolved(owner, source_branch_fingerprint, "known_active", "exception_applies")
    return _resolved(owner, source_branch_fingerprint, "known_active", "confirmed_blocked")

def finalize_bind_manual_switch_candidates(*, base_candidates: Sequence[Mapping[str, Any]], manual_permission: Mapping[str, Any], branch_state: Mapping[str, Any], source_branch_fingerprint: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    block=derive_bind_manual_switch_block(branch_state=branch_state, source_branch_fingerprint=source_branch_fingerprint, owner=owner)
    if block.get("status") != "resolved": return block
    permission=normalize_switch_permission_context(manual_permission, session_id=owner["session_id"], active_slot_index=owner["slot_index"], active_pokemon_id=owner["pokemon_id"])
    return {"status":"resolved", "source_branch_fingerprint":source_branch_fingerprint, "owner":deepcopy(dict(owner)), "bind_switch_restriction":block, "manual_permission":permission, "switch_candidates":finalize_switch_candidates(base_candidates, manual_permission=permission, blocker={"state":block["block_state"]})}

def _resolved(owner: Mapping[str, Any], fp: str, state: str, block: str) -> dict[str, Any]: return {"status":"resolved", "session_id":owner["session_id"], "source_branch_fingerprint":fp, "owner":deepcopy(dict(owner)), "bind_state":state, "block_state":block, "provenance":"trusted_observed_bind_result_v1"}
def _result(status: str, reason: str) -> dict[str, Any]: return {"status":status,"reason":reason}
