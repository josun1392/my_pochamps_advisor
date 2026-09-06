from copy import deepcopy
from advisor.canonical_rage_fist_hit_count_power_family import resolve_canonical_rage_fist_hit_count_power_move
from llm.advisor_reducer_state_model import project_atomic_transition,state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_rage_fist_hit_count_authority import freeze_runtime_d0_rage_fist_hit_count_authority
from llm.advisor_detached_rage_fist_hit_count_power_authority import materialize_detached_rage_fist_hit_count_power_authority
from tests.test_runtime_d0_native_damage_context import _state
def _owner(s):p=s['self_side']['pokemon'][0];return {'session_id':s['session_id'],'side':'self','slot_index':0,'pokemon_id':p['pokemon_id']}
def _step(s,e,seq=1):o=_owner(s);return project_atomic_transition(s,{'session_id':s['session_id'],'status':'planned','conflicts':[],'replay_policy_version':'v1','ordered_steps':[{'observation_id':e,'observation_sequence':seq,'planned_effect':e,'trust':'user_confirmed_observation',**o,'turn_number':1,'hit_outcome':'successful_direct_hit'}]},s['session_id'])['projected_state']
def test_catalog_and_persistent_counter_power():
 assert resolve_canonical_rage_fist_hit_count_power_move(move={'move_id':'rage-fist'})['effect']['maximum_power']==350
 s=_state('rage');s=_step(s,'initialize_rage_fist_hit_count');s=_step(s,'record_rage_fist_qualifying_hit',2);snap={'status':'runtime_snapshot_ready','session_id':s['session_id'],'state':deepcopy(s),'state_fingerprint':state_fingerprint(s)};d=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s));a=freeze_runtime_d0_rage_fist_hit_count_authority(strategy_d0=d,runtime_snapshot=snap,owner=_owner(s));assert a['battle_received_hit_count']==1
 move={'move_id':'rage-fist','type':'ghost','category':'physical','power':50,'accuracy':100,'priority':0,'contact':True};p=materialize_detached_rage_fist_hit_count_power_authority(strategy_d0=d,move=move,user=_owner(s),base_count_authority=a);assert p['selected_base_power']==100

def test_cap_and_same_turn_successful_hit_overlay_only():
 s=_step(_state('rage-cap'),'initialize_rage_fist_hit_count');snap={'status':'runtime_snapshot_ready','session_id':s['session_id'],'state':deepcopy(s),'state_fingerprint':state_fingerprint(s)};d=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s));a=freeze_runtime_d0_rage_fist_hit_count_authority(strategy_d0=d,runtime_snapshot=snap,owner=_owner(s));a['battle_received_hit_count']=7
 move={'move_id':'rage-fist','type':'ghost','category':'physical','power':50,'accuracy':100,'priority':0,'contact':True};leaf={'leaf_id':'hit','candidate_id':'attack:tackle','hit_state':'hit','consequences':{'damage':0},'provenance':{'target':_owner(s),'move_id':'tackle'}}
 p=materialize_detached_rage_fist_hit_count_power_authority(strategy_d0=d,move=move,user=_owner(s),base_count_authority=a,source_terminal_leaf=leaf);assert (p['same_turn_hit_increment'],p['effective_hit_count'],p['selected_base_power'])==(1,8,350)
 leaf['hit_state']='miss';assert materialize_detached_rage_fist_hit_count_power_authority(strategy_d0=d,move=move,user=_owner(s),base_count_authority=a,source_terminal_leaf=leaf)['same_turn_hit_increment']==0
