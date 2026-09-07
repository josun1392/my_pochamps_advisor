"""Immutable completion authority for Magician/Pickpocket item-steal triggers."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION="runtime-d0-ability-item-steal-completion-authority-v1"
_DIRECTIONS={"magician_attacker_hit":"magician","pickpocket_defender_contact":"pickpocket"}

def freeze_runtime_d0_ability_item_steal_completion_authority(*, bindings:Mapping[str,Any], ability_state:Mapping[str,Any], receiver_item:Mapping[str,Any], donor_item:Mapping[str,Any], legality:Mapping[str,Any], completion:Mapping[str,Any], contact:Mapping[str,Any]|None=None, sheer_force:Mapping[str,Any]|None=None)->dict[str,Any]:
    """Classify one already-completed action without mutating D0 or inventory."""
    direction=bindings.get("trigger_direction") if isinstance(bindings,Mapping) else None; ability=bindings.get("ability_id") if isinstance(bindings,Mapping) else None
    if direction not in _DIRECTIONS or ability!=_DIRECTIONS[direction]: return _bad("rejected","ability_direction_binding_invalid")
    receiver,donor=bindings.get("receiver"),bindings.get("donor")
    if not all(isinstance(x,Mapping) for x in (receiver,donor)) or receiver==donor or bindings.get("ability_holder")!=receiver: return _bad("rejected","ability_item_steal_identity_invalid")
    if ability_state.get("status")=="unknown" or receiver_item.get("status")=="unknown" or donor_item.get("status")=="unknown" or legality.get("status")!="resolved": return _bad("incomplete","ability_item_steal_required_authority_unknown")
    if ability_state.get("status")!="active": return _result("suppressed_ability",bindings,receiver_item,donor_item)
    if completion.get("status")!="completed" or not isinstance(completion.get("terminal_id"),str): return _result("not_completed_action",bindings,receiver_item,donor_item)
    if direction=="pickpocket_defender_contact":
        if not isinstance(contact,Mapping) or contact.get("status")!="resolved": return _bad("incomplete","pickpocket_contact_authority_unknown")
        if contact.get("is_contact") is not True:return _result("non_contact",bindings,receiver_item,donor_item)
        if not isinstance(sheer_force,Mapping) or sheer_force.get("status")!="resolved":return _bad("incomplete","pickpocket_sheer_force_authority_unknown")
        if sheer_force.get("prevents_trigger") is True:return _result("blocked_sheer_force",bindings,receiver_item,donor_item)
    if receiver_item.get("status")!="known_absent":return _result("receiver_already_has_item",bindings,receiver_item,donor_item)
    if donor_item.get("status")!="known":return _result("donor_has_no_item",bindings,receiver_item,donor_item)
    if legality.get("sticky_hold_active") is True:return _result("blocked_sticky_hold",bindings,receiver_item,donor_item)
    if legality.get("transferable") is not True:return _bad("incomplete","item_transfer_legality_unknown")
    item=donor_item.get("value")
    if not isinstance(item,str) or not item:return _bad("rejected","donor_item_identity_invalid")
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(bindings)),"completion":deepcopy(dict(completion)),"contact":deepcopy(dict(contact)) if isinstance(contact,Mapping) else None,"sheer_force_trigger_applicability":deepcopy(dict(sheer_force)) if isinstance(sheer_force,Mapping) else None,"receiver_item_before":deepcopy(dict(receiver_item)),"donor_item_before":deepcopy(dict(donor_item)),"transfer_legality":deepcopy(dict(legality)),"outcome":"transferred","item":item,"receiver_item_after":{"status":"known","value":item},"donor_item_after":{"status":"known_absent","value":None},"provenance":"strict_runtime_d0_ability_item_steal_completion_v1"}

def materialize_detached_direction_neutral_item_transfer(*,authority:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(authority,Mapping) or authority.get("schema_version")!=SCHEMA_VERSION or authority.get("status")!="resolved":return _bad("rejected","ability_item_steal_authority_invalid")
    if authority.get("outcome")!="transferred" or authority.get("receiver_item_after",{}).get("value")!=authority.get("item") or authority.get("donor_item_after",{}).get("value") is not None:return _bad("rejected","ability_item_steal_atomicity_invalid")
    return {"status":"resolved","authority":deepcopy(dict(authority)),"receiver":deepcopy(dict(authority["receiver"])),"donor":deepcopy(dict(authority["donor"])),"item":authority["item"],"receiver_item_after":deepcopy(dict(authority["receiver_item_after"])),"donor_item_after":deepcopy(dict(authority["donor_item_after"])),"provenance":"detached_direction_neutral_ability_item_transfer_v1"}

def _result(outcome:str,b:Mapping[str,Any],r:Mapping[str,Any],d:Mapping[str,Any])->dict[str,Any]:return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(b)),"receiver_item_before":deepcopy(dict(r)),"donor_item_before":deepcopy(dict(d)),"receiver_item_after":deepcopy(dict(r)),"donor_item_after":deepcopy(dict(d)),"outcome":outcome,"provenance":"strict_runtime_d0_ability_item_steal_completion_v1"}
def _bad(status:str,reason:str)->dict[str,Any]:return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
