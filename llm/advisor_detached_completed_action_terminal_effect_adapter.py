"""Typed, detached post-terminal consequence boundary.

Source owners establish terminality; this adapter only validates and carries
that evidence without traversing or flattening a graph.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION="detached-completed-action-terminal-effect-adapter-v1"
_FAMILIES=frozenset({"ordinary_single_hit","fixed_two_hit","variable_two_to_five_hit","population_bomb","triple_axel","triple_kick"})

def bind_native_terminal_source(*, family:str, terminal_edge:Mapping[str,Any], action_id:str, move_id:str, actor:Mapping[str,Any], target:Mapping[str,Any])->dict[str,Any]:
    """Owner-local bridge: expose, but never infer, a native terminal edge."""
    if family not in _FAMILIES or not isinstance(terminal_edge,Mapping):return _bad("rejected","native_terminal_source_invalid")
    if terminal_edge.get("terminal") is not True or not isinstance(terminal_edge.get("edge_id"),str):return _bad("rejected","native_terminal_source_not_terminal")
    return {"status":"resolved","family":family,"terminal":True,"terminal_id":terminal_edge["edge_id"],"terminal_reason":terminal_edge.get("terminal_reason"),"action_id":action_id,"move_id":move_id,"actor":deepcopy(dict(actor)),"target":deepcopy(dict(target)),"native_terminal":deepcopy(dict(terminal_edge)),"provenance":"native_terminal_edge_to_typed_terminal_source_v1"}

def attach_detached_completed_action_terminal_effect(*, terminal_source:Mapping[str,Any], detached_state:Mapping[str,Any], effect_kind:str, effect_authority:Mapping[str,Any], sheer_force:Mapping[str,Any]|None=None)->dict[str,Any]:
    """Attach one already-resolved deterministic terminal consequence."""
    if not isinstance(terminal_source,Mapping) or terminal_source.get("family") not in _FAMILIES:return _bad("rejected","terminal_effect_source_family_invalid")
    if terminal_source.get("terminal") is not True or not isinstance(terminal_source.get("terminal_id"),str):return _bad("rejected","terminal_effect_source_not_terminal")
    if not isinstance(detached_state,Mapping) or detached_state.get("status")!="resolved":return _bad("incomplete","terminal_effect_detached_state_unknown")
    first=detached_state.get("first_action")
    if not isinstance(first,Mapping) or first.get("candidate_id")!=terminal_source.get("action_id") or first.get("move_id")!=terminal_source.get("move_id"):return _bad("rejected","terminal_effect_action_identity_mismatch")
    if effect_kind!="ability_item_steal" or not isinstance(effect_authority,Mapping):return _bad("rejected","terminal_effect_kind_unsupported")
    if effect_authority.get("trigger_direction")=="pickpocket_defender_contact" and (terminal_source.get("actor")!=effect_authority.get("donor") or terminal_source.get("target")!=effect_authority.get("receiver")):return _bad("rejected","terminal_effect_participant_mismatch")
    if isinstance(sheer_force,Mapping) and sheer_force.get("status")!="resolved":return _bad("incomplete","terminal_effect_sheer_force_unknown")
    if isinstance(sheer_force,Mapping) and any(sheer_force.get(k) not in {None,terminal_source.get(k)} for k in ("action_id","move_id")):return _bad("rejected","terminal_effect_sheer_force_identity_mismatch")
    result="applied" if effect_authority.get("status")=="resolved" and effect_authority.get("outcome")=="transferred" else "exact_no_effect" if effect_authority.get("status")=="resolved" else effect_authority.get("status","incomplete")
    after = deepcopy(dict(detached_state))
    if result == "applied":
        item = effect_authority.get("item")
        if not isinstance(item, str) or effect_authority.get("receiver_item_after") != {"status": "known", "value": item} or effect_authority.get("donor_item_after") != {"status": "known_absent", "value": None} or effect_authority.get("receiver_item_before", {}).get("status") != "known_absent" or effect_authority.get("donor_item_before", {}).get("value") != item or effect_authority.get("donor_item_before", {}).get("status") != "known":
            return _bad("rejected", "terminal_effect_atomicity_invalid")
        receiver, donor = effect_authority.get("receiver"), effect_authority.get("donor")
        if not isinstance(receiver, Mapping) or not isinstance(donor, Mapping) or receiver == donor:
            return _bad("rejected", "terminal_effect_participant_mismatch")
        if effect_authority.get("trigger_direction") == "magician_attacker_hit" and (receiver != terminal_source.get("actor") or donor != terminal_source.get("target")):
            return _bad("rejected", "terminal_effect_participant_mismatch")
        for owner, item_key in ((receiver, "receiver_item_after"), (donor, "donor_item_after")):
            active = after.get("active", {}).get(owner.get("side"))
            item = effect_authority.get(item_key)
            if not isinstance(active, dict) or active.get("owner") != owner or not isinstance(item, Mapping):
                return _bad("rejected", "terminal_effect_item_projection_invalid")
            active["hypothetical_item"] = deepcopy(dict(item))
    return {"status":"resolved" if result in {"applied","exact_no_effect"} else result,"schema_version":SCHEMA_VERSION,"terminal_source":deepcopy(dict(terminal_source)),"detached_state_before":deepcopy(dict(detached_state)),"effect_kind":effect_kind,"effect_authority":deepcopy(dict(effect_authority)),"sheer_force":deepcopy(dict(sheer_force)) if isinstance(sheer_force,Mapping) else None,"result":result,"detached_state_after":after,"provenance":"typed_completed_action_terminal_effect_v1"}

def _bad(status:str,reason:str)->dict[str,Any]:return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
