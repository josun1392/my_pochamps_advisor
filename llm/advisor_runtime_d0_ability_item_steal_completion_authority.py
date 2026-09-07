"""Immutable completion authority for Magician/Pickpocket item-steal triggers."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from advisor.canonical_knock_off_item_power_and_removal import resolve_knock_off_target_item

SCHEMA_VERSION="runtime-d0-ability-item-steal-completion-authority-v1"
_DIRECTIONS={"magician_attacker_hit":"magician","pickpocket_defender_contact":"pickpocket"}

def bind_branch_time_ability_item_steal_items(*, intermediate_state: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    """Read the detached, path-local held-item overlay; never fall back to D0.

    This is deliberately an adapter over ``detached_predictive_intermediate_state``.
    That owner has already applied exact Knock Off/Fling/Thief-style item effects, so
    using its hypothetical item is required when the steal trigger is later in a path.
    """
    base = _binding_base(bindings)
    if not isinstance(intermediate_state, Mapping) or intermediate_state.get("status") != "resolved":
        return _bad("incomplete", "ability_item_steal_branch_state_unknown")
    if any(intermediate_state.get(k) != v for k, v in base.items()):
        return _bad("rejected", "ability_item_steal_branch_state_provenance_mismatch")
    active = intermediate_state.get("active")
    receiver, donor = bindings.get("receiver"), bindings.get("donor")
    if not isinstance(active, Mapping) or not isinstance(receiver, Mapping) or not isinstance(donor, Mapping):
        return _bad("rejected", "ability_item_steal_branch_state_identity_invalid")
    receiver_row, donor_row = active.get(receiver.get("side")), active.get(donor.get("side"))
    if not isinstance(receiver_row, Mapping) or not isinstance(donor_row, Mapping) or receiver_row.get("owner") != receiver or donor_row.get("owner") != donor:
        return _bad("rejected", "ability_item_steal_branch_state_owner_mismatch")
    return {"status": "resolved", "receiver_item": _branch_item(receiver_row.get("hypothetical_item")), "donor_item": _branch_item(donor_row.get("hypothetical_item")), "provenance": "exact_detached_branch_item_overlay_v1"}

def bind_final_ability_item_steal_contact(*, source_terminal_leaf: Mapping[str, Any], intermediate_state: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    """Bind Pickpocket to a final leaf's contact result, not move category."""
    check = _terminal_leaf_binding(source_terminal_leaf, intermediate_state, bindings)
    if isinstance(check, str): return _bad("rejected", check)
    if bindings.get("trigger_direction") != "pickpocket_defender_contact":
        return {"status": "not_applicable", "provenance": "magician_does_not_consume_contact_authority_v1"}
    contact = _mapping(source_terminal_leaf.get("consequences")).get("contact")
    if contact == "successful_contact_eligible":
        return {"status": "resolved", "is_contact": True, "source_leaf_id": source_terminal_leaf["leaf_id"], "action_id": bindings["action_id"], "move_id": bindings["move_id"], "provenance": "exact_terminal_leaf_final_contact_v1"}
    if contact in {"not_applicable", "successful_non_contact"}:
        return {"status": "resolved", "is_contact": False, "source_leaf_id": source_terminal_leaf["leaf_id"], "action_id": bindings["action_id"], "move_id": bindings["move_id"], "provenance": "exact_terminal_leaf_final_contact_v1"}
    return _bad("incomplete", "pickpocket_final_contact_unknown")

def bind_completed_ability_item_steal_action(*, intermediate_state: Mapping[str, Any], bindings: Mapping[str, Any], graph: Mapping[str, Any] | None = None, terminal_edge: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Convert existing terminal-leaf/graph ownership into one completion witness.

    A graph edge is accepted only when it is one of the graph's own terminal
    edges.  This keeps intermediate multi-hit edges from impersonating action
    completion and preserves early terminal reasons such as miss or a KO.
    """
    base = _binding_base(bindings)
    if not isinstance(intermediate_state, Mapping) or intermediate_state.get("status") != "resolved" or any(intermediate_state.get(k) != v for k, v in base.items()):
        return _bad("rejected", "ability_item_steal_completion_state_provenance_mismatch")
    first = intermediate_state.get("first_action")
    if not isinstance(first, Mapping) or first.get("candidate_id") != bindings.get("action_id") or first.get("move_id") != bindings.get("move_id") or not isinstance(first.get("leaf_id"), str):
        return _bad("rejected", "ability_item_steal_completion_action_identity_mismatch")
    if graph is None and terminal_edge is None:
        return {"status": "completed", "terminal_id": first["leaf_id"], "action_id": bindings["action_id"], "move_id": bindings["move_id"], "terminal_reason": "exact_terminal_leaf", "provenance": "detached_intermediate_terminal_leaf_v1"}
    if not isinstance(graph, Mapping) or graph.get("status") != "evaluable" or any(graph.get(k) != v for k, v in base.items()) or not isinstance(terminal_edge, Mapping):
        return _bad("rejected", "ability_item_steal_terminal_graph_invalid")
    edges = graph.get("terminal_leaf_edges")
    if not isinstance(edges, tuple) or terminal_edge not in edges:
        return _bad("rejected", "ability_item_steal_terminal_edge_foreign")
    if terminal_edge.get("terminal") is not True or not isinstance(terminal_edge.get("edge_id"), str):
        return _bad("rejected", "ability_item_steal_action_not_terminal")
    return {"status": "completed", "terminal_id": terminal_edge["edge_id"], "action_id": bindings["action_id"], "move_id": bindings["move_id"], "terminal_reason": terminal_edge.get("terminal_reason"), "provenance": "exact_existing_multi_hit_terminal_graph_edge_v1"}

def freeze_runtime_d0_ability_item_steal_completion_from_branch(*, strategy_d0: Mapping[str, Any], bindings: Mapping[str, Any], ability_state: Mapping[str, Any], legality: Mapping[str, Any], intermediate_state: Mapping[str, Any], source_terminal_leaf: Mapping[str, Any], graph: Mapping[str, Any] | None = None, terminal_edge: Mapping[str, Any] | None = None, sheer_force: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Compose production-owned branch evidence without dispatching either ability."""
    base = _binding_base(bindings)
    if not isinstance(strategy_d0, Mapping) or strategy_d0.get("status") != "resolved" or any(strategy_d0.get(k) != v for k, v in base.items()):
        return _bad("rejected", "ability_item_steal_strategy_d0_provenance_mismatch")
    items = bind_branch_time_ability_item_steal_items(intermediate_state=intermediate_state, bindings=bindings)
    completion = bind_completed_ability_item_steal_action(intermediate_state=intermediate_state, bindings=bindings, graph=graph, terminal_edge=terminal_edge)
    if items.get("status") != "resolved": return items
    if completion.get("status") != "completed": return completion
    contact = bind_final_ability_item_steal_contact(source_terminal_leaf=source_terminal_leaf, intermediate_state=intermediate_state, bindings=bindings)
    if bindings.get("trigger_direction") == "pickpocket_defender_contact" and contact.get("status") != "resolved": return contact
    return freeze_runtime_d0_ability_item_steal_completion_authority(bindings=bindings, ability_state=ability_state, receiver_item=items["receiver_item"], donor_item=items["donor_item"], legality=legality, completion=completion, contact=contact if contact.get("status") == "resolved" else None, sheer_force=sheer_force)

def freeze_runtime_d0_ability_item_steal_completion_from_snapshot(*,strategy_d0:Mapping[str,Any],runtime_snapshot:Mapping[str,Any],trigger_direction:str,ability_holder:Mapping[str,Any],donor:Mapping[str,Any],completion:Mapping[str,Any],contact:Mapping[str,Any]|None=None,sheer_force:Mapping[str,Any]|None=None)->dict[str,Any]:
    """Read only current runtime facts; production still owns trigger dispatch."""
    if not isinstance(strategy_d0,Mapping) or strategy_d0.get("status")!="resolved" or not isinstance(runtime_snapshot,Mapping):return _bad("rejected","ability_item_steal_runtime_d0_invalid")
    ability=_DIRECTIONS.get(trigger_direction)
    if ability is None:return _bad("rejected","ability_item_steal_direction_invalid")
    state=runtime_snapshot.get("state");
    def raw(owner:Mapping[str,Any])->Any:
        side=state.get(f"{owner.get('side')}_side") if isinstance(state,Mapping) else None; roster=side.get("pokemon") if isinstance(side,Mapping) else None
        return roster.get(owner.get("slot_index")) if isinstance(roster,Mapping) else None
    holder,donor_raw=raw(ability_holder),raw(donor)
    if not isinstance(holder,Mapping) or not isinstance(donor_raw,Mapping):return _bad("rejected","ability_item_steal_runtime_identity_invalid")
    ability_value=holder.get("current_ability"); donor_ability=donor_raw.get("current_ability")
    gas=ability_value=="neutralizing-gas" or donor_ability=="neutralizing-gas"
    ability_state={"status":"active" if ability_value==ability and not gas else "suppressed" if isinstance(ability_value,str) else "unknown","value":ability_value,"neutralizing_gas_active":gas}
    item=lambda row:{"status":"known","value":row.get("known_item")} if isinstance(row.get("known_item"),str) and row.get("known_item") else {"status":"known_absent","value":None} if row.get("known_item") is None and isinstance(row.get("known_item_provenance"),Mapping) else {"status":"unknown","value":None}
    receiver_item,donor_item=item(holder),item(donor_raw)
    bindings={"ability_id":ability,"trigger_direction":trigger_direction,"ability_holder":deepcopy(dict(ability_holder)),"receiver":deepcopy(dict(ability_holder)),"donor":deepcopy(dict(donor)),"session_id":strategy_d0.get("session_id"),"source_runtime_fingerprint":strategy_d0.get("source_runtime_fingerprint"),"source_branch_fingerprint":strategy_d0.get("strategy_preview_fingerprint"),"action_id":completion.get("action_id"),"move_id":completion.get("move_id")}
    removable=resolve_knock_off_target_item(item_authority=donor_item,target_species=donor_raw.get("pokemon_identity") if isinstance(donor_raw.get("pokemon_identity"),str) else None)
    legality={"status":"resolved" if removable.get("status")=="resolved" else "unknown","transferable":removable.get("removable"),"sticky_hold_active":donor_ability=="sticky-hold" and not gas,"donor_ability":donor_ability,"neutralizing_gas_active":gas,"donor":deepcopy(dict(donor)),"removability_authority":removable}
    return freeze_runtime_d0_ability_item_steal_completion_authority(bindings=bindings,ability_state=ability_state,receiver_item=receiver_item,donor_item=donor_item,legality=legality,completion=completion,contact=contact,sheer_force=sheer_force)

def freeze_runtime_d0_ability_item_steal_completion_authority(*, bindings:Mapping[str,Any], ability_state:Mapping[str,Any], receiver_item:Mapping[str,Any], donor_item:Mapping[str,Any], legality:Mapping[str,Any], completion:Mapping[str,Any], contact:Mapping[str,Any]|None=None, sheer_force:Mapping[str,Any]|None=None)->dict[str,Any]:
    """Classify one already-completed action without mutating D0 or inventory."""
    direction=bindings.get("trigger_direction") if isinstance(bindings,Mapping) else None; ability=bindings.get("ability_id") if isinstance(bindings,Mapping) else None
    if direction not in _DIRECTIONS or ability!=_DIRECTIONS[direction]: return _bad("rejected","ability_direction_binding_invalid")
    receiver,donor=bindings.get("receiver"),bindings.get("donor")
    if not all(isinstance(x,Mapping) for x in (receiver,donor)) or receiver==donor or bindings.get("ability_holder")!=receiver: return _bad("rejected","ability_item_steal_identity_invalid")
    if ability_state.get("status")=="unknown" or receiver_item.get("status")=="unknown" or donor_item.get("status")=="unknown" or legality.get("status")!="resolved": return _bad("incomplete","ability_item_steal_required_authority_unknown")
    if ability_state.get("status")!="active": return _result("suppressed_ability",bindings,receiver_item,donor_item)
    if completion.get("status")!="completed" or not isinstance(completion.get("terminal_id"),str): return _result("not_completed_action",bindings,receiver_item,donor_item)
    if any(completion.get(k) not in {None, bindings.get(k)} for k in ("action_id", "move_id")): return _bad("rejected","ability_item_steal_completion_identity_mismatch")
    if direction=="pickpocket_defender_contact":
        if not isinstance(contact,Mapping) or contact.get("status")!="resolved": return _bad("incomplete","pickpocket_contact_authority_unknown")
        if any(contact.get(k) not in {None, bindings.get(k)} for k in ("action_id", "move_id")): return _bad("rejected","pickpocket_contact_identity_mismatch")
        if contact.get("is_contact") is not True:return _result("non_contact",bindings,receiver_item,donor_item)
        if not isinstance(sheer_force,Mapping) or sheer_force.get("status")!="resolved":return _bad("incomplete","pickpocket_sheer_force_authority_unknown")
        if any(sheer_force.get(k) not in {None, bindings.get(k)} for k in ("action_id", "move_id")): return _bad("rejected","pickpocket_sheer_force_identity_mismatch")
        if sheer_force.get("prevents_trigger") is True:return _result("blocked_sheer_force",bindings,receiver_item,donor_item)
    if receiver_item.get("status")!="known_absent":return _result("receiver_already_has_item",bindings,receiver_item,donor_item)
    if donor_item.get("status")!="known":return _result("donor_has_no_item",bindings,receiver_item,donor_item)
    if legality.get("donor") is not None and legality.get("donor") != donor:return _bad("rejected","item_transfer_legality_donor_mismatch")
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
def _mapping(value: Any) -> Mapping[str, Any]: return value if isinstance(value, Mapping) else {}
def _binding_base(bindings: Mapping[str, Any]) -> dict[str, Any]: return {k: bindings.get(k) for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")}
def _branch_item(value: Any) -> dict[str, Any]:
    row = _mapping(value); status = row.get("status")
    if status == "known" and isinstance(row.get("value"), str) and row["value"]: return {"status":"known","value":row["value"],"source":"exact_branch_item_overlay"}
    if status in {"known_absent", "known_none"} and row.get("value") is None: return {"status":"known_absent","value":None,"source":"exact_branch_item_overlay"}
    return {"status":"unknown","value":None,"reason":"branch_time_held_item_unknown"}
def _terminal_leaf_binding(leaf: Any, state: Any, bindings: Mapping[str, Any]) -> str | None:
    if not isinstance(leaf, Mapping) or not isinstance(state, Mapping) or state.get("status") != "resolved": return "ability_item_steal_terminal_leaf_invalid"
    first = state.get("first_action"); provenance = leaf.get("provenance")
    if not isinstance(first, Mapping) or not isinstance(provenance, Mapping): return "ability_item_steal_terminal_leaf_provenance_missing"
    if leaf.get("leaf_id") != first.get("leaf_id") or leaf.get("candidate_id") != bindings.get("action_id") or provenance.get("move_id") != bindings.get("move_id"): return "ability_item_steal_terminal_leaf_identity_mismatch"
    attacker, target = provenance.get("attacker"), provenance.get("target")
    if bindings.get("trigger_direction") == "magician_attacker_hit":
        if attacker != bindings.get("receiver") or target != bindings.get("donor"): return "ability_item_steal_magician_actor_target_mismatch"
    elif attacker != bindings.get("donor") or target != bindings.get("receiver"):
        return "ability_item_steal_pickpocket_actor_target_mismatch"
    return None
