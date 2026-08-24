"""Private session-scoped canonical observation buffer."""
from copy import deepcopy

_KINDS={"direct_move_damage_observed","used_move_observed","exact_hp_transition_observed","exact_hp_recovery_observed","current_type_observed","current_weather_observed","current_ability_observed","current_level_observed","substitute_state_observed","pokemon_switch_observed","pokemon_faint_observed","condition_applied_observed","stat_stage_observed","switch_hazards_observed","tailwind_side_condition_observed","trick_room_field_observed","same_turn_event_observed","first_end_of_turn_reached_observed"}
class ObservationCollection:
 def __init__(self,session_id): self._session_id=session_id; self._items={}
 def add_confirmation_result(self,result):
  if not isinstance(result,dict) or result.get("status")!="confirmed" or not isinstance(result.get("observation"),dict): return {"status":"ignored"}
  item=deepcopy(result["observation"]); oid,seq=item.get("observation_id"),item.get("observation_sequence")
  if item.get("session_id")!=self._session_id:return {"status":"stale_session"}
  turn=item.get("turn_number")
  if not isinstance(oid,str) or not oid or not isinstance(seq,int) or isinstance(seq,bool) or seq<1 or not _valid_turn_number(turn) or item.get("event_kind") not in _KINDS:return {"status":"invalid_observation"}
  old=self._items.get(oid)
  if old is not None:return {"status":"duplicate" if old==item else "conflicting_confirmation"}
  self._items[oid]=item;return {"status":"added"}
 def snapshot(self,session_id=None):
  if session_id is not None and session_id!=self._session_id:return {"status":"session_mismatch","session_id":self._session_id,"ordered_observations":[]}
  return {"status":"ready","session_id":self._session_id,"ordered_observations":deepcopy(sorted(self._items.values(),key=lambda x:(x["observation_sequence"],x["observation_id"]))),"limitations":["structured_only","no_store_or_reducer_application","no_provider_calls"]}
 def start_new_session(self,session_id): self._session_id=session_id;self._items={};return self.snapshot()

def _valid_turn_number(value): return value is None or (isinstance(value,int) and not isinstance(value,bool) and value>0)
