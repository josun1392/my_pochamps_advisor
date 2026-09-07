from copy import deepcopy
import pytest
from llm.advisor_runtime_d0_ability_item_steal_completion_authority import freeze_runtime_d0_ability_item_steal_completion_authority as freeze, materialize_detached_direction_neutral_item_transfer as materialize, bind_branch_time_ability_item_steal_items, bind_final_ability_item_steal_contact, bind_completed_ability_item_steal_action, freeze_runtime_d0_ability_item_steal_completion_from_branch

R={"side":"self","pokemon_id":"r"};D={"side":"opponent","pokemon_id":"d"}
def call(direction="magician_attacker_hit",**over):
 b={"ability_id":"magician" if direction.startswith("magician") else "pickpocket","trigger_direction":direction,"ability_holder":R,"receiver":R,"donor":D,"action_id":"a","move_id":"tackle","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b"}
 a={"status":"active"};ri={"status":"known_absent","value":None};di={"status":"known","value":"black-belt"};l={"status":"resolved","transferable":True,"sticky_hold_active":False};c={"status":"completed","terminal_id":"a:terminal"};contact={"status":"resolved","is_contact":True};sheer={"status":"resolved","prevents_trigger":False}
 for key,value in over.items(): {"bindings":b,"ability_state":a,"receiver_item":ri,"donor_item":di,"legality":l,"completion":c,"contact":contact,"sheer_force":sheer}[key].update(value)
 return freeze(bindings=b,ability_state=a,receiver_item=ri,donor_item=di,legality=l,completion=c,contact=contact,sheer_force=sheer)
def test_magician_and_pickpocket_directions_are_explicit_and_atomic():
 m=call(); p=call("pickpocket_defender_contact")
 assert m["outcome"]==p["outcome"]=="transferred"
 assert materialize(authority=m)["receiver_item_after"]["value"]=="black-belt"
 assert materialize(authority=p)["receiver"]==R and materialize(authority=p)["donor"]==D
def test_preconditions_and_exact_pickpocket_contact_fail_closed():
 assert call(receiver_item={"status":"known","value":"orb"})["outcome"]=="receiver_already_has_item"
 assert call(donor_item={"status":"known_absent","value":None})["outcome"]=="donor_has_no_item"
 assert call(ability_state={"status":"suppressed"})["outcome"]=="suppressed_ability"
 assert call("pickpocket_defender_contact",contact={"is_contact":False})["outcome"]=="non_contact"
 assert call("pickpocket_defender_contact",sheer_force={"prevents_trigger":True})["outcome"]=="blocked_sheer_force"
def test_completion_sticky_hold_unknown_and_forged_atomicity_are_rejected():
 assert call(completion={"status":"intermediate","terminal_id":"a:1"})["outcome"]=="not_completed_action"
 assert call(legality={"sticky_hold_active":True})["outcome"]=="blocked_sticky_hold"
 assert call(receiver_item={"status":"unknown"})["status"]=="incomplete"
 x=call(); x["donor_item_after"]={"status":"known","value":"black-belt"}; assert materialize(authority=x)["status"]=="rejected"

def _branch(direction="magician_attacker_hit", *, receiver_item=None, donor_item=None):
    b={"ability_id":"magician" if direction.startswith("magician") else "pickpocket","trigger_direction":direction,"ability_holder":R,"receiver":R,"donor":D,"action_id":"a","move_id":"tackle","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b"}
    leaf={"leaf_id":"a:terminal","candidate_id":"a","action_type":"attack","consequences":{"contact":"successful_contact_eligible"},"provenance":{"attacker":D if direction.startswith("pickpocket") else R,"target":R if direction.startswith("pickpocket") else D,"move_id":"tackle"}}
    state={"status":"resolved","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b","first_action":{"candidate_id":"a","move_id":"tackle","leaf_id":"a:terminal"},"active":{"self":{"owner":R,"hypothetical_item":receiver_item or {"status":"known_absent","value":None}},"opponent":{"owner":D,"hypothetical_item":donor_item or {"status":"known","value":"black-belt"}}}}
    return b,leaf,state

def test_branch_item_adapter_reads_exact_overlay_not_d0_and_fails_closed():
 b,_,state=_branch(receiver_item={"status":"known","value":"orb"},donor_item={"status":"known_absent","value":None})
 got=bind_branch_time_ability_item_steal_items(intermediate_state=state,bindings=b)
 assert got["receiver_item"]["value"]=="orb" and got["donor_item"]["status"]=="known_absent"
 state["active"]["self"]["hypothetical_item"]={"status":"unknown"};assert bind_branch_time_ability_item_steal_items(intermediate_state=state,bindings=b)["receiver_item"]["status"]=="unknown"

def test_final_contact_is_leaf_bound_and_pickpocket_reverse_direction_is_strict():
 b,leaf,state=_branch("pickpocket_defender_contact")
 assert bind_final_ability_item_steal_contact(source_terminal_leaf=leaf,intermediate_state=state,bindings=b)["is_contact"] is True
 leaf["consequences"]["contact"]="successful_non_contact";assert bind_final_ability_item_steal_contact(source_terminal_leaf=leaf,intermediate_state=state,bindings=b)["is_contact"] is False
 leaf["provenance"]["attacker"]=R;assert bind_final_ability_item_steal_contact(source_terminal_leaf=leaf,intermediate_state=state,bindings=b)["status"]=="rejected"

def test_completion_accepts_terminal_graph_edges_only_and_preserves_early_terminal_reason():
 b,_,state=_branch(); edge={"edge_id":"a:hit:2","terminal":True,"terminal_reason":"target_fainted"}; graph={"status":"evaluable","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b","terminal_leaf_edges":(edge,)}
 done=bind_completed_ability_item_steal_action(intermediate_state=state,bindings=b,graph=graph,terminal_edge=edge)
 assert done["status"]=="completed" and done["terminal_reason"]=="target_fainted"
 edge["terminal"]=False;assert bind_completed_ability_item_steal_action(intermediate_state=state,bindings=b,graph=graph,terminal_edge=edge)["status"]=="rejected"

def test_branch_composition_uses_terminal_contact_and_donor_direction_legality():
 b,leaf,state=_branch("pickpocket_defender_contact")
 d0={"status":"resolved","session_id":"s","source_runtime_fingerprint":"r","source_branch_fingerprint":"b"}
 out=freeze_runtime_d0_ability_item_steal_completion_from_branch(strategy_d0=d0,bindings=b,ability_state={"status":"active"},legality={"status":"resolved","transferable":True,"sticky_hold_active":False,"donor":D},intermediate_state=state,source_terminal_leaf=leaf,sheer_force={"status":"resolved","prevents_trigger":False,"action_id":"a","move_id":"tackle"})
 assert out["outcome"]=="transferred" and out["receiver"]==R
 out=freeze_runtime_d0_ability_item_steal_completion_from_branch(strategy_d0=d0,bindings=b,ability_state={"status":"active"},legality={"status":"resolved","transferable":True,"sticky_hold_active":True,"donor":D},intermediate_state=state,source_terminal_leaf=leaf,sheer_force={"status":"resolved","prevents_trigger":False})
 assert out["outcome"]=="blocked_sticky_hold"
 assert call(legality={"donor":R})["status"]=="rejected"
