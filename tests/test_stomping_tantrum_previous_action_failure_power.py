from copy import deepcopy
import pytest
from advisor.canonical_previous_action_failure_power_family import resolve_canonical_previous_action_failure_power_move, qualifies_as_previous_move_failure
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_previous_action_result_authority import freeze_runtime_d0_previous_action_result_authority
from llm.advisor_detached_previous_action_failure_power_authority import materialize_previous_action_failure_power_authority
from tests.test_runtime_d0_native_damage_context import _state

def _owner(s, side="self"):
    p=s[f"{side}_side"]["pokemon"][0]; return {"session_id":s["session_id"],"side":side,"slot_index":0,"pokemon_id":p["pokemon_id"]}
def _snap(s): return {"status":"runtime_snapshot_ready","session_id":s["session_id"],"state":deepcopy(s),"state_fingerprint":state_fingerprint(s)}
def _record(s, result="success", selected="tackle", execution=None):
    o=_owner(s); execution=execution or selected
    steps=[
        {"observation_id":"executed-action","observation_sequence":1,"planned_effect":"record_executed_move","trust":"user_confirmed_observation",**o,"turn_number":1,"move_id":execution,"source_action_id":"attack:tackle"},
        {"observation_id":"prior-action","observation_sequence":2,"planned_effect":"record_previous_action_result","trust":"user_confirmed_observation",**o,"turn_number":1,"previous_action_id":"attack:tackle","selected_move_id":selected,"execution_move_id":execution,"result_class":result},
    ]
    return project_atomic_transition(s,{"session_id":s["session_id"],"status":"planned","conflicts":[],"replay_policy_version":"v1","ordered_steps":steps},s["session_id"])["projected_state"]
def _authority(s):
    snap=_snap(s); d0=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s)); prior=freeze_runtime_d0_previous_action_result_authority(strategy_d0=d0,runtime_snapshot=snap,owner=_owner(s)); return materialize_previous_action_failure_power_authority(strategy_d0=d0,move={"move_id":"stomping-tantrum","type":"ground","category":"physical","power":75,"accuracy":100,"priority":0,"contact":True},user=_owner(s),previous_action_authority=prior)

def test_catalog_and_explicit_failure_policy():
    effect=resolve_canonical_previous_action_failure_power_move(move={"move_id":"stomping-tantrum"})["effect"]
    assert (effect["type"],effect["category"],effect["power"],effect["contact"]) == ("ground","physical",75,True)
    assert resolve_canonical_previous_action_failure_power_move(move={"move_id":"tackle"})["status"] == "unsupported"
    assert qualifies_as_previous_move_failure("protection_block") is False
    assert all(qualifies_as_previous_move_failure(x) is True for x in ("accuracy_miss","type_or_ability_immunity","move_specific_failure","full_paralysis","flinch","sleep","freeze"))
    assert qualifies_as_previous_move_failure("unclassified") is None

def test_missing_unknown_success_failure_and_unsupported_fail_closed():
    s=_state("tantrum")
    assert _authority(s)["status"] == "incomplete"
    assert _authority(_record(s))["selected_base_power"] == 75
    assert _authority(_record(s,"accuracy_miss"))["selected_base_power"] == 150
    assert _authority(_record(s,"unclassified"))["status"] == "incomplete"

def test_identity_selected_execution_and_stale_forgery_rejected():
    s=_record(_state("tantrum-id"),"move_specific_failure",selected="tackle",execution="quick-attack")
    authority=_authority(s); assert authority["selected_base_power"] == 150 and authority["selected_move_id"] == "tackle" and authority["execution_move_id"] == "quick-attack"
    snap=_snap(s); d0=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s)); assert freeze_runtime_d0_previous_action_result_authority(strategy_d0=d0,runtime_snapshot=snap,owner={**_owner(s),"pokemon_id":"foreign"})["status"] == "rejected"
    forged=deepcopy(s); forged["self_side"]["pokemon"][0]["previous_action_result"]["owner"]["pokemon_id"]="foreign"
    assert freeze_runtime_d0_previous_action_result_authority(strategy_d0=d0,runtime_snapshot=_snap(forged),owner=_owner(s))["status"] == "rejected"
    order_state=_state("tantrum-order"); o=_owner(order_state)
    stale_steps=[
        {"observation_id":"early-result","observation_sequence":1,"planned_effect":"record_previous_action_result","trust":"user_confirmed_observation",**o,"turn_number":1,"previous_action_id":"attack:tackle","selected_move_id":"tackle","execution_move_id":"tackle","result_class":"accuracy_miss"},
        {"observation_id":"late-execution","observation_sequence":2,"planned_effect":"record_executed_move","trust":"user_confirmed_observation",**o,"turn_number":1,"move_id":"tackle","source_action_id":"attack:tackle"},
    ]
    stale=project_atomic_transition(order_state,{"session_id":o["session_id"],"status":"planned","conflicts":[],"replay_policy_version":"v1","ordered_steps":stale_steps},o["session_id"])["projected_state"]
    stale_snap=_snap(stale); stale_d0=freeze_runtime_strategy_d0(runtime_snapshot=stale_snap,decision_owner=o)
    assert freeze_runtime_d0_previous_action_result_authority(strategy_d0=stale_d0,runtime_snapshot=stale_snap,owner=o)["reason"] == "previous_action_result_order_stale"

def test_later_executed_move_invalidates_an_older_failure_result():
    s=_state("tantrum-stale")
    o=_owner(s)
    steps=[
        {"observation_id":"tackle-executed","observation_sequence":1,"planned_effect":"record_executed_move","trust":"user_confirmed_observation",**o,"turn_number":1,"move_id":"tackle","source_action_id":"attack:tackle"},
        {"observation_id":"tackle-miss","observation_sequence":2,"planned_effect":"record_previous_action_result","trust":"user_confirmed_observation",**o,"turn_number":1,"previous_action_id":"attack:tackle","selected_move_id":"tackle","execution_move_id":"tackle","result_class":"accuracy_miss"},
        {"observation_id":"scratch-executed","observation_sequence":3,"planned_effect":"record_executed_move","trust":"user_confirmed_observation",**o,"turn_number":2,"move_id":"scratch","source_action_id":"attack:scratch"},
    ]
    stale=project_atomic_transition(s,{"session_id":s["session_id"],"status":"planned","conflicts":[],"replay_policy_version":"v1","ordered_steps":steps},s["session_id"])["projected_state"]
    authority=_authority(stale)
    assert authority["status"] == "incomplete"
    assert authority["reason"] == "previous_action_result_history_missing"
