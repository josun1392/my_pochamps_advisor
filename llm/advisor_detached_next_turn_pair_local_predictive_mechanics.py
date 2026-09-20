"""Authenticated hypothetical overlay of one detached first-action leaf."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_next_turn_predictive_mechanics_authority import validate_next_turn_predictive_mechanics_authority
from llm.advisor_detached_next_turn_ordinary_attack_execution import validate_detached_next_turn_ordinary_attack_execution_authority

SCHEMA_VERSION="detached-next-turn-pair-local-predictive-mechanics-authority-v1"

def materialize_detached_next_turn_pair_local_predictive_mechanics(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,predictive_mechanics:Mapping[str,Any],first_action_execution:Mapping[str,Any],first_action_ledger:Mapping[str,Any],first_leaf_id:str)->dict[str,Any]:
    if validate_next_turn_predictive_mechanics_authority(authority=predictive_mechanics,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _r("rejected","root_predictive_mechanics_authority_invalid")
    source=first_action_execution.get("execution_authority") if isinstance(first_action_execution,Mapping) and "execution_authority" in first_action_execution else first_action_execution
    if validate_detached_next_turn_ordinary_attack_execution_authority(authority=source,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _r("rejected","first_action_execution_authority_invalid")
    ledger=first_action_ledger.get("action_ledger") if isinstance(first_action_ledger,Mapping) and "action_ledger" in first_action_ledger else first_action_ledger
    if not isinstance(ledger,Mapping) or ledger.get("status")!="resolved" or ledger.get("execution_authority")!=source.get("action"):return _r("rejected","first_action_ledger_authority_mismatch")
    leaf=next((x for x in ledger.get("terminal_leaves",()) if isinstance(x,Mapping) and x.get("leaf_id")==first_leaf_id),None)
    if leaf is None:return _r("rejected","first_action_leaf_not_in_authenticated_ledger")
    actor,target=source["action"]["actor"],source["action"]["target"]
    rows=deepcopy(dict(predictive_mechanics["sides"])); consequences=leaf.get("consequences",{})
    selected_not_execute=consequences.get("selected_move_does_not_execute") is True
    err=_hp(rows[actor["side"]],consequences.get("own_final_hp"));
    if err:return _r("rejected",err)
    if not selected_not_execute:
        err=_hp(rows[target["side"]],consequences.get("target_final_hp"));
        if err:return _r("rejected",err)
    manifest={"hp": [actor["side"]]+([] if selected_not_execute else [target["side"]])}
    if consequences.get("target_item_after")=={"status":"known_absent","value":None}:
        rows[target["side"]]["item"]={"status":"known_absent"}; manifest["item"]=[target["side"]]
    secondary=consequences.get("secondary")
    pending={"status":"known_not_flinched"}
    if isinstance(secondary,Mapping) and secondary.get("state")=="status_applied" and secondary.get("condition") in {"paralysis","burn"} and isinstance(secondary.get("authority"),Mapping) and secondary["authority"].get("status")=="resolved":
        rows[target["side"]]["condition"]={"status":"known_present","condition":secondary["condition"]}; rows[target["side"]]["status_progression"]={"status":"not_applicable"}; manifest["condition"]=[target["side"]]
    elif isinstance(secondary,Mapping) and secondary.get("state")=="flinched" and isinstance(secondary.get("authority"),Mapping) and secondary["authority"].get("status")=="resolved":
        pending={"status":"known_flinched","owner":deepcopy(dict(target)),"source_leaf_id":first_leaf_id,"secondary_authority":deepcopy(dict(secondary["authority"]))}
    _sync(rows[actor["side"]]); _sync(rows[target["side"]])
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"source_next_decision_fingerprint":next_decision_fingerprint,"root_predictive_mechanics_authority":deepcopy(dict(predictive_mechanics)),"first_action_execution_authority":deepcopy(dict(source)),"first_action_ledger":deepcopy(dict(ledger)),"first_leaf_id":first_leaf_id,"first_actor":deepcopy(dict(actor)),"first_target":deepcopy(dict(target)),"sides":rows,"pending_action_flinch":pending,"represented_mutation_manifest":manifest,"provenance":"authenticated_detached_next_turn_pair_local_predictive_mechanics_v1"}

def validate_detached_next_turn_pair_local_predictive_mechanics(*,authority:Any,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,**kwargs:Any)->str|None:
    if not isinstance(authority,Mapping):return "pair_local_predictive_mechanics_authority_invalid"
    expected=materialize_detached_next_turn_pair_local_predictive_mechanics(next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint,predictive_mechanics=kwargs.get("predictive_mechanics",authority.get("root_predictive_mechanics_authority")),first_action_execution=kwargs.get("first_action_execution",authority.get("first_action_execution_authority")),first_action_ledger=kwargs.get("first_action_ledger",authority.get("first_action_ledger")),first_leaf_id=kwargs.get("first_leaf_id",authority.get("first_leaf_id")))
    return None if expected==authority else "pair_local_predictive_mechanics_authority_mismatch"
def _hp(row,hp):
    if not isinstance(hp,int):return None
    current=row.get("current_hp",{}); maximum=current.get("maximum_hp")
    if not isinstance(maximum,int) or not 0<=hp<=maximum:return "pair_local_hp_invalid"
    current["current_hp"]=hp; row["current_hp"]=current; row["fainted"]=hp==0
def _sync(row):
    direct=row.get("direct_mechanics",{}); combatant=direct.get("combatant") if isinstance(direct,Mapping) else None
    if isinstance(combatant,dict):
        hp=row["current_hp"]; combatant["current_hp"]=hp["current_hp"];combatant["max_hp"]=hp["maximum_hp"];combatant["item"]=row.get("item",{}).get("value") if row.get("item",{}).get("status")=="known" else None;combatant["status"]=row.get("condition",{}).get("condition") if row.get("condition",{}).get("status")=="known_present" else None
def _r(status,reason):return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
