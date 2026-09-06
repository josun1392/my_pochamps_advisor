from advisor.canonical_same_turn_stat_drop_power_family import resolve_canonical_same_turn_stat_drop_power_move
from llm.advisor_detached_same_turn_stat_drop_power_authority import materialize_detached_same_turn_stat_drop_power_authority

def _d0():
    user={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}; target={"session_id":"s","side":"opponent","slot_index":0,"pokemon_id":"b"}
    return {"status":"resolved","session_id":"s","source_runtime_fingerprint":"r","strategy_preview_fingerprint":"b","decision_owner":user,"active_owners":{"self":user,"opponent":target}},user,target
def _move(): return {"move_id":"lash-out","type":"dark","category":"physical","power":75,"accuracy":100,"priority":0,"contact":True}
def _leaf(user,before,after,target=None): return {"leaf_id":"leaf","candidate_id":"attack:tail-whip","stage_transition":{"target":target or user,"stat":"attack","pre_stage":before,"post_stage":after,"actual_delta":after-before},"provenance":{"move_id":"tail-whip","attacker":{"side":"opponent"}}}

def test_catalog_and_actual_stage_decrease_only():
    effect=resolve_canonical_same_turn_stat_drop_power_move(move=_move())["effect"]
    assert (effect["type"],effect["category"],effect["power"],effect["priority"],effect["contact"]) == ("dark","physical",75,0,True)
    assert resolve_canonical_same_turn_stat_drop_power_move(move={"move_id":"tackle"})["status"]=="unsupported"
    d,user,_=_d0()
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user)["selected_base_power"]==75
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user,source_terminal_leaf=_leaf(user,0,-1))["selected_base_power"]==150
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user,source_terminal_leaf=_leaf(user,-1,-2))["selected_base_power"]==150
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user,source_terminal_leaf=_leaf(user,-6,-6))["selected_base_power"]==75
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user,source_terminal_leaf=_leaf(user,0,1))["selected_base_power"]==75

def test_identity_and_forgery_fail_closed():
    d,user,other=_d0()
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user,source_terminal_leaf=_leaf(user,0,-1,target=other))["status"]=="rejected"
    bad=_leaf(user,0,-1); bad["stage_transition"]["stat"]="made-up"
    assert materialize_detached_same_turn_stat_drop_power_authority(strategy_d0=d,move=_move(),user=user,source_terminal_leaf=bad)["status"]=="rejected"
