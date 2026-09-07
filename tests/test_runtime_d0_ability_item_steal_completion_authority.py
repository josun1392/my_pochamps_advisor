from copy import deepcopy
import pytest
from llm.advisor_runtime_d0_ability_item_steal_completion_authority import freeze_runtime_d0_ability_item_steal_completion_authority as freeze, materialize_detached_direction_neutral_item_transfer as materialize

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
