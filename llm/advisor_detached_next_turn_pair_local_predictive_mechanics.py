"""Authenticated hypothetical overlay of one detached first-action leaf."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_next_turn_predictive_mechanics_authority import validate_next_turn_predictive_mechanics_authority
from llm.advisor_detached_next_turn_ordinary_attack_execution import validate_detached_next_turn_ordinary_attack_execution_authority, validate_detached_next_turn_ordinary_attack_execution
from llm.advisor_detached_standard_charge_turn_two_attack_execution import AUTHORITY_SCHEMA_VERSION as CHARGE_AUTHORITY_SCHEMA_VERSION, validate_detached_standard_charge_turn_two_attack_execution

SCHEMA_VERSION="detached-next-turn-pair-local-predictive-mechanics-authority-v1"

def materialize_detached_next_turn_pair_local_predictive_mechanics(*,next_decision_state:Mapping[str,Any],next_decision_fingerprint:str,predictive_mechanics:Mapping[str,Any],first_action_execution:Mapping[str,Any],first_action_ledger:Mapping[str,Any],first_leaf_id:str)->dict[str,Any]:
    if validate_next_turn_predictive_mechanics_authority(authority=predictive_mechanics,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _r("rejected","root_predictive_mechanics_authority_invalid")
    source=first_action_execution.get("execution_authority") if isinstance(first_action_execution,Mapping) and "execution_authority" in first_action_execution else first_action_execution
    family="ordinary"
    if source.get("schema_version")==CHARGE_AUTHORITY_SCHEMA_VERSION:
        family="standard_charge"
        if validate_detached_standard_charge_turn_two_attack_execution(result=first_action_ledger,execution_authority=source) is not None:return _r("rejected","first_action_ledger_execution_mismatch")
        candidates=[row for row in first_action_ledger.get("actions",{}).values() if isinstance(row,Mapping) and row.get("status")=="resolved"]
        ledger=next((row for row in candidates if any(x.get("leaf_id")==first_leaf_id for x in row.get("terminal_leaves",()))),None)
    else:
        if validate_detached_next_turn_ordinary_attack_execution_authority(authority=source,next_decision_state=next_decision_state,next_decision_fingerprint=next_decision_fingerprint) is not None:return _r("rejected","first_action_execution_authority_invalid")
        if isinstance(first_action_ledger,Mapping) and "action_ledger" in first_action_ledger and validate_detached_next_turn_ordinary_attack_execution(result=first_action_ledger,execution_authority=source) is not None:return _r("rejected","first_action_ledger_execution_mismatch")
        ledger=first_action_ledger.get("action_ledger") if isinstance(first_action_ledger,Mapping) and "action_ledger" in first_action_ledger else first_action_ledger
    if not isinstance(ledger,Mapping) or ledger.get("status")!="resolved":return _r("rejected","first_action_ledger_authority_mismatch")
    action=ledger.get("execution_authority")
    if not isinstance(action,Mapping):return _r("rejected","first_action_ledger_action_missing")
    leaf=next((x for x in ledger.get("terminal_leaves",()) if isinstance(x,Mapping) and x.get("leaf_id")==first_leaf_id),None)
    if leaf is None:return _r("rejected","first_action_leaf_not_in_authenticated_ledger")
    actor,target=action["actor"],action["target"]
    if _unrepresented_pre_action_transition(leaf):return _r("incomplete","pair_local_pre_action_state_transition_unrepresented")
    rows=deepcopy(dict(predictive_mechanics["sides"])); consequences=leaf.get("consequences",{})
    selected_not_execute=consequences.get("selected_move_does_not_execute") is True
    err=_hp(rows[actor["side"]],consequences.get("own_final_hp"));
    if err:return _r("rejected",err)
    if not selected_not_execute:
        err=_hp(rows[target["side"]],consequences.get("target_final_hp"));
        if err:return _r("rejected",err)
    manifest={"hp": [actor["side"]]+([] if selected_not_execute else [target["side"]])}
    if _focus_sash_consumed(consequences,action,actor,target,leaf):
        rows[target["side"]]["item"]={"status":"known_absent"}; manifest["item"]=[target["side"]]
    elif consequences.get("target_item_after")=={"status":"known_absent","value":None}:return _r("rejected","pair_local_focus_sash_consumption_unauthenticated")
    secondary=consequences.get("secondary")
    pending={"status":"known_not_flinched"}
    if _status_secondary(secondary,action,target,leaf):
        rows[target["side"]]["condition"]={"status":"known_present","condition":secondary["condition"]}; rows[target["side"]]["status_progression"]={"status":"not_applicable"}; manifest["condition"]=[target["side"]]
    elif isinstance(secondary,Mapping) and secondary.get("state")=="status_applied":return _r("rejected","pair_local_status_secondary_unauthenticated")
    elif _flinch_secondary(secondary,action,target,leaf):
        pending={"status":"known_flinched","owner":deepcopy(dict(target)),"source_leaf_id":first_leaf_id,"secondary_authority":deepcopy(dict(secondary["authority"]))}
    elif isinstance(secondary,Mapping) and secondary.get("state")=="flinched":return _r("rejected","pair_local_flinch_secondary_unauthenticated")
    _sync(rows[actor["side"]]); _sync(rows[target["side"]])
    # A standard-charge result contains both forced continuations.  Preserve
    # that authenticated result (rather than only its selected action ledger)
    # so validation can rematerialize the exact source leaf later.
    source_ledger = first_action_ledger if family == "standard_charge" else ledger
    return {"status":"resolved","schema_version":SCHEMA_VERSION,"first_action_family":family,"source_next_decision_fingerprint":next_decision_fingerprint,"root_predictive_mechanics_authority":deepcopy(dict(predictive_mechanics)),"first_action_execution_authority":deepcopy(dict(source)),"first_action_ledger":deepcopy(dict(source_ledger)),"first_leaf_id":first_leaf_id,"first_actor":deepcopy(dict(actor)),"first_target":deepcopy(dict(target)),"sides":rows,"pending_action_flinch":pending,"represented_mutation_manifest":manifest,"provenance":"authenticated_detached_next_turn_pair_local_predictive_mechanics_v1"}

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
def _focus_sash_consumed(c,action,actor,target,leaf):
    sash=c.get("focus_sash_survival") if isinstance(c,Mapping) else None
    if not isinstance(sash,Mapping) or sash.get("status")!="resolved" or sash.get("outcome")!="activated" or c.get("target_item_after")!={"status":"known_absent","value":None}:return False
    source=sash.get("source_authority")
    hit=leaf.get("damage_roll",{}) if isinstance(leaf,Mapping) else {}
    return isinstance(source,Mapping) and source.get("holder")==target and source.get("attacker")==actor and source.get("continuation_action_id")==action.get("continuation_action_id") and sash.get("source_action_id")==action.get("continuation_action_id") and sash.get("source_hit_id")==f"roll:{hit.get('roll_index')}" and isinstance(c.get("raw_damage"),int)
def _status_secondary(secondary,action,target,leaf):
    cap=secondary.get("authority") if isinstance(secondary,Mapping) else None
    condition=secondary.get("condition") if isinstance(secondary,Mapping) else None
    return isinstance(cap,Mapping) and secondary.get("state")=="status_applied" and condition in {"paralysis","burn"} and cap.get("schema_version")=="probabilistic-target-status-effect-capability-resolution-v1" and cap.get("status")=="resolved" and cap.get("move_id")==action.get("move_id") and cap.get("effect")=={"owner":"target","condition":condition} and cap.get("probability",{}).get("numerator",0)>0 and leaf.get("provenance",{}).get("target")==target
def _flinch_secondary(secondary,action,target,leaf):
    cap=secondary.get("authority") if isinstance(secondary,Mapping) else None; marker=secondary.get("hypothetical_target_flinch") if isinstance(secondary,Mapping) else None
    return isinstance(cap,Mapping) and isinstance(marker,Mapping) and secondary.get("state")=="flinched" and marker.get("schema_version")=="detached-hypothetical-immediate-flinch-v1" and marker.get("state")=="flinched" and cap.get("schema_version")=="probabilistic-target-flinch-effect-capability-resolution-v1" and cap.get("status")=="resolved" and cap.get("move_id")==action.get("move_id") and cap.get("effect",{}).get("owner")=="target" and leaf.get("provenance",{}).get("target")==target
def _unrepresented_pre_action_transition(leaf):
    path=leaf.get("branch_path",()) if isinstance(leaf,Mapping) else ()
    text=" ".join(str(x) for x in path).lower()
    return any(token in text for token in ("wake","thaw","snap_out","snap-out","snapped_out","snapped out"))
def _r(status,reason):return {"status":status,"schema_version":SCHEMA_VERSION,"reason":reason}
