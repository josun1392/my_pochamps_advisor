from copy import deepcopy
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (build_runtime_d0_native_damage_context, build_runtime_d0_strict_hit_chance_assessment, freeze_runtime_current_stage_authority, freeze_runtime_strategy_d0)
from tests.test_runtime_d0_native_damage_context import _state as _native_state

KEYS=("attack","defense","special-attack","special-defense","speed","accuracy","evasion")
def _state(session="stage-authority"): return _native_state(session)
def _owner(state,side="self"): return {"session_id":state["session_id"],"side":side,"slot_index":0,"pokemon_id":state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}
def _snapshot(state): return {"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":deepcopy(state),"state_fingerprint":state_fingerprint(state)}
def _d0(state):
    snapshot=_snapshot(state); return snapshot,freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state))

def test_seven_stage_partial_zero_detached_and_stale_bound_authority():
    state=_state(); state["self_side"]["pokemon"][0]["stat_stages"]={"attack":0,"accuracy":2}; snapshot,d0=_d0(state)
    authority=freeze_runtime_current_stage_authority(strategy_d0=d0,runtime_snapshot=snapshot,owner=_owner(state))
    assert authority["stages"]["attack"]["value"]==0 and authority["stages"]["accuracy"]["value"]==2
    assert authority["stages"]["evasion"]["status"]=="unknown" and set(authority["stages"])==set(KEYS)
    state["self_side"]["pokemon"][0]["stat_stages"]["attack"]=6
    assert authority["stages"]["attack"]["value"]==0
    assert freeze_runtime_current_stage_authority(strategy_d0=d0,runtime_snapshot=_snapshot(state),owner=_owner(state))["status"]=="rejected"

def test_native_five_stage_ignores_unknown_accuracy_evasion_and_hit_is_strict():
    state=_state()
    for side in ("self","opponent"): state[f"{side}_side"]["pokemon"][0]["stat_stages"]={key:0 for key in KEYS[:5]}
    snapshot,d0=_d0(state)
    native=build_runtime_d0_native_damage_context(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),move_metadata={"move_id":"water-gun","category":"special","power":40,"type":"water"})
    assert native["stat_provenance"]["attacker"]["stat_stages"]["available"] is True
    assert len(native["snapshot_damage_input"]["battle_context"]["current_state"]["stat_stage_context"]["current_stages"])==10
    strict=build_runtime_d0_strict_hit_chance_assessment(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),selected_move={"move_id":"water-gun","accuracy":100})
    assert strict["status"]=="incomplete" and strict["reason"]=="attacker_accuracy_stage"

def test_strict_hit_zero_and_nonzero_use_canonical_arithmetic():
    state=_state(); state["self_side"]["pokemon"][0]["stat_stages"]={"accuracy":0}; state["opponent_side"]["pokemon"][0]["stat_stages"]={"evasion":0}
    snapshot,d0=_d0(state); result=build_runtime_d0_strict_hit_chance_assessment(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),selected_move={"move_id":"x","accuracy":80})
    assert result["assessment"]["net_stage"]==0 and result["assessment"]["hit_chance_percent"]==80
    state["self_side"]["pokemon"][0]["stat_stages"]["accuracy"]=2; state["opponent_side"]["pokemon"][0]["stat_stages"]["evasion"]=1
    snapshot,d0=_d0(state); result=build_runtime_d0_strict_hit_chance_assessment(strategy_d0=d0,runtime_snapshot=snapshot,attacker=_owner(state),target=_owner(state,"opponent"),selected_move={"move_id":"x","accuracy":80})
    assert result["assessment"]["net_stage"]==1 and result["assessment"]["hit_chance_percent"]==100
