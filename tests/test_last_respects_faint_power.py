from copy import deepcopy
from advisor.canonical_last_respects_faint_power_family import resolve_canonical_last_respects_faint_power_move
from llm.advisor_runtime_d0_last_respects_faint_history_authority import freeze_runtime_d0_last_respects_faint_history_authority
from llm.advisor_detached_last_respects_faint_power_authority import materialize_detached_last_respects_faint_power_authority
from tests.test_runtime_d0_native_damage_context import _state
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
def _owner(s):p=s['self_side']['pokemon'][0];return {'session_id':s['session_id'],'side':'self','slot_index':0,'pokemon_id':p['pokemon_id']}
def test_catalog_missing_and_raw_history_mapping():
 s=_state('respects');snap={'status':'runtime_snapshot_ready','session_id':s['session_id'],'state':deepcopy(s),'state_fingerprint':state_fingerprint(s)};d=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s));assert freeze_runtime_d0_last_respects_faint_history_authority(strategy_d0=d,runtime_snapshot=snap,owner=_owner(s))['status']=='incomplete'
 s['supreme_overlord_faint_history_context']={'schema_version':'supreme-overlord-faint-history-context-v1','session_id':s['session_id'],'side_counts':{'self':3,'opponent':5},'initialized_sides':['self'],'provenance':{'event_kind':'pokemon_faint_observed','source_sequence':1}};snap={'status':'runtime_snapshot_ready','session_id':s['session_id'],'state':deepcopy(s),'state_fingerprint':state_fingerprint(s)};d=freeze_runtime_strategy_d0(runtime_snapshot=snap,decision_owner=_owner(s));a=freeze_runtime_d0_last_respects_faint_history_authority(strategy_d0=d,runtime_snapshot=snap,owner=_owner(s));move={'move_id':'last-respects','type':'ghost','category':'physical','power':50,'accuracy':100,'priority':0,'contact':False};p=materialize_detached_last_respects_faint_power_authority(strategy_d0=d,move=move,user=_owner(s),history_authority=a);assert (p['raw_allied_faint_count'],p['selected_base_power'])==(3,200)
 assert resolve_canonical_last_respects_faint_power_move(move=move)['effect']['contact'] is False
