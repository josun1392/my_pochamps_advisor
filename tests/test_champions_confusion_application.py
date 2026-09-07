from copy import deepcopy
import pytest
from tests.test_detached_opponent_response_profile import _state,_complete_state,_owner,_snapshot
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_champions_confusion_application import freeze_champions_confusion_application as freeze,materialize_champions_confusion_application as materialize

def inputs(move="confuse-ray",outcome="hit",**changes):
    state=_complete_state(_state()); state["field"]["terrain"]="none"; state["identity_groundedness_context"]={"schema_version":"identity-groundedness-v1","session_id":state["session_id"],"side":"opponent","slot_index":0,"pokemon_id":"opponent-a","status":"grounded"}
    for path,value in changes.items():
        target=state["opponent_side"]["pokemon"][0] if path.startswith("target_") else state["self_side"]["pokemon"][0]
        target[path.removeprefix("target_")]=value
    snapshot=_snapshot(state);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state,"self"));source,target=_owner(state,"self"),_owner(state,"opponent");action={"action_id":f"attack:{move}","action_type":"attack","identity":move};base={"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"source":source,"target":target,"action_id":action["action_id"],"move_id":move};success={"status":"resolved",**base,"outcome":outcome,**({"damage_resolved":True} if move=="dynamic-punch" and outcome=="hit" else {})};return snapshot,d0,source,target,action,success

def test_confuse_ray_establishes_existing_confusion_owner_and_input_stays_immutable():
    snapshot,d0,source,target,action,success=inputs();before=deepcopy((snapshot,d0));authority=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success);result=materialize(authority=authority,runtime_snapshot=snapshot)
    raw=result["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0];assert authority["prevention_outcome"]=="applies" and raw["current_confusion"]=="confused" and raw["champions_confusion_progression"]["duration"] is None
    assert (snapshot,d0)==before

def test_application_reuses_the_existing_confusion_action_gate_owner():
    from llm.advisor_champions_confusion_action_gate import freeze_champions_confusion_action_gate
    snapshot,d0,source,target,action,success=inputs(); application=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success); result=materialize(authority=application,runtime_snapshot=snapshot); next_d0=freeze_runtime_strategy_d0(runtime_snapshot=result["runtime_snapshot"],decision_owner=target)
    gate=freeze_champions_confusion_action_gate(strategy_d0=next_d0,runtime_snapshot=result["runtime_snapshot"],actor=target,action_id="opponent_attack:tackle",move_id="tackle",action_order={"order":"own_first"})
    assert gate["status"]=="resolved" and gate["confusion"]=="confused"

@pytest.mark.parametrize("outcome,expected",[("missed","move_missed"),("blocked_by_protection","blocked_by_protection")])
def test_confuse_ray_miss_and_protection_do_not_establish(outcome,expected):
    snapshot,d0,source,target,action,success=inputs(outcome=outcome);a=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success);r=materialize(authority=a,runtime_snapshot=snapshot);assert r["outcome"]==expected and not r["confusion_applied"]

def test_own_tempo_misty_safeguard_and_substitute_are_independent_blocks():
    for field,value,expected in [("target_current_ability","own-tempo","blocked_by_own_tempo"),("target_current_confusion","confused","already_confused_no_new_application")]:
        snapshot,d0,source,target,action,success=inputs(**{field:value});assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["prevention_outcome"]==expected
    snapshot,d0,source,target,action,success=inputs();snapshot=deepcopy(snapshot);snapshot["state"]["field"]["terrain"]="misty";snapshot=_snapshot(snapshot["state"]);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=source);success.update(source_runtime_fingerprint=d0["source_runtime_fingerprint"],source_branch_fingerprint=d0["strategy_preview_fingerprint"]);assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["prevention_outcome"]=="blocked_by_misty_terrain"
    snapshot,d0,source,target,action,success=inputs();snapshot=deepcopy(snapshot);snapshot["state"]["opponent_side"]["side_conditions"]=["safeguard"];snapshot=_snapshot(snapshot["state"]);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=source);success.update(source_runtime_fingerprint=d0["source_runtime_fingerprint"],source_branch_fingerprint=d0["strategy_preview_fingerprint"]);assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["prevention_outcome"]=="blocked_by_safeguard"
    snapshot,d0,source,target,action,success=inputs();snapshot=deepcopy(snapshot);snapshot["state"]["substitute_state_context"]["states"][1]["state"]="known_active";snapshot["state"]["substitute_state_context"]["states"][1]["substitute_hp"]=25;snapshot=_snapshot(snapshot["state"]);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=source);success.update(source_runtime_fingerprint=d0["source_runtime_fingerprint"],source_branch_fingerprint=d0["strategy_preview_fingerprint"]);assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["prevention_outcome"]=="blocked_by_substitute"
    snapshot,d0,source,target,action,success=inputs();snapshot=deepcopy(snapshot);snapshot["state"]["self_side"]["pokemon"][0]["current_ability"]="infiltrator";snapshot["state"]["substitute_state_context"]["states"][1]["state"]="known_active";snapshot["state"]["substitute_state_context"]["states"][1]["substitute_hp"]=25;snapshot=_snapshot(snapshot["state"]);d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=source);success.update(source_runtime_fingerprint=d0["source_runtime_fingerprint"],source_branch_fingerprint=d0["strategy_preview_fingerprint"]);assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["prevention_outcome"]=="applies"

def test_swagger_keeps_attack_plus_two_when_confusion_is_prevented_or_present():
    snapshot,d0,source,target,action,success=inputs("swagger",target_current_ability="own-tempo");a=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success);r=materialize(authority=a,runtime_snapshot=snapshot);assert r["outcome"]=="blocked_by_own_tempo" and r["swagger_stage_transition"]["delta"]==2
    snapshot,d0,source,target,action,success=inputs("swagger",target_current_confusion="confused");a=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success);r=materialize(authority=a,runtime_snapshot=snapshot);assert r["outcome"]=="already_confused_no_new_application" and r["swagger_stage_transition"]["delta"]==2

def test_teeter_dance_and_dynamic_punch_use_the_same_establishment_path():
    for move in ("teeter-dance","dynamic-punch"):
        snapshot,d0,source,target,action,success=inputs(move);a=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success);assert materialize(authority=a,runtime_snapshot=snapshot)["confusion_applied"]

def test_teeter_dance_is_explicitly_bounded_to_singles():
    snapshot,d0,source,target,action,success=inputs("teeter-dance"); snapshot=deepcopy(snapshot); snapshot["state"]["field"]["battle_format"]="doubles"; snapshot=_snapshot(snapshot["state"]); d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=source); success.update(source_runtime_fingerprint=d0["source_runtime_fingerprint"],source_branch_fingerprint=d0["strategy_preview_fingerprint"])
    assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["reason"]=="teeter_dance_singles_only"

def test_dynamic_punch_rejects_secondary_before_a_bound_successful_hit():
    snapshot,d0,source,target,action,success=inputs("dynamic-punch");success.pop("damage_resolved");assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success)["status"]=="rejected"

def test_reflected_application_and_tampered_authority_do_not_materialize():
    snapshot,d0,source,target,action,success=inputs(); reflection={key:success[key] for key in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","source","target","action_id","move_id")}; reflection["outcome"]="reflected"
    assert freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success,reflection_authority=reflection)["reason"]=="reflected_confusion_application_owner_unavailable"
    authority=freeze(strategy_d0=d0,runtime_snapshot=snapshot,source=source,target=target,action=action,move_success_authority=success); authority["prevention_outcome"]="blocked_by_own_tempo"
    assert materialize(authority=authority,runtime_snapshot=snapshot)["reason"]=="confusion_application_provenance_invalid"
