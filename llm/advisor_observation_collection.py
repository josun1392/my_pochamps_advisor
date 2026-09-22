"""Private session-scoped canonical observation buffer."""
from copy import deepcopy
from llm.advisor_switch_entry_mechanics_derived_observation import (
    DERIVED_KINDS, MECHANICS_DERIVED_TRUST, SWITCH_ENTRY_MECHANICS_SOURCE,
)
from llm.advisor_champions_status_action_lifecycle_derived_observation import (
    DERIVED_KINDS as STATUS_ACTION_DERIVED_KINDS, MECHANICS_DERIVED_TRUST as STATUS_ACTION_TRUST,
    CHAMPIONS_STATUS_ACTION_LIFECYCLE_SOURCE,
)
from llm.advisor_champions_confusion_action_lifecycle_derived_observation import (
    DERIVED_KINDS as CONFUSION_ACTION_DERIVED_KINDS, MECHANICS_DERIVED_TRUST as CONFUSION_ACTION_TRUST,
    CHAMPIONS_CONFUSION_ACTION_LIFECYCLE_SOURCE,
)
from llm.advisor_confusion_self_hit_damage_lifecycle import (
    DERIVED_KINDS as CONFUSION_SELF_HIT_DAMAGE_DERIVED_KINDS,
    SOURCE as CONFUSION_SELF_HIT_DAMAGE_DERIVED_SOURCE,
    TRUST as CONFUSION_SELF_HIT_DAMAGE_DERIVED_TRUST,
)

_KINDS={"direct_move_damage_observed","used_move_observed","exact_hp_transition_observed","exact_hp_recovery_observed","current_type_observed","current_weather_observed","current_ability_observed","current_item_observed","current_terrain_observed","current_side_conditions_observed","current_battle_format_observed","current_level_observed","current_final_combat_stat_observed","current_opponent_response_set_observed","current_opponent_switch_response_set_observed","current_opponent_switch_target_combat_observed","substitute_state_observed","pokemon_switch_observed","pokemon_faint_observed","condition_applied_observed","stat_stage_observed","switch_hazards_observed","tailwind_side_condition_observed","trick_room_field_observed","magic_room_field_observed","gravity_field_observed","current_locked_on_state_observed","same_turn_event_observed","first_end_of_turn_reached_observed"}
_KINDS.update({"executed_move_observed", "previous_action_result_observed", "flinch_causality_observed"})
_KINDS.add("contact_reactive_status_result_observed")
_KINDS.add("contact_reactive_damage_result_observed")
_KINDS.update({"taunt_restriction_applied_observed", "encore_restriction_applied_observed", "disable_restriction_applied_observed", "taunt_restricted_turn_completed_observed", "encore_restricted_turn_completed_observed", "disable_restricted_turn_completed_observed"})
_KINDS.update({"current_aqua_ring_state_observed", "current_ingrain_state_observed", "current_leech_seed_state_observed"})
_KINDS.add("current_condition_observed")
_KINDS.add("berry_eaten_state_observed")
_KINDS.update({"current_confusion_state_observed", "champions_confusion_progression_observed", "champions_status_progression_observed"})
# These lifecycle-confirmed observations have canonical replay/reducer owners and
# are intended to enter the normal production runtime pipeline.  Keep fixture
# transitions and special evidence-only observations out of this admission set.
_KINDS.update({
 "current_healing_prevented_observed",
 "pending_status_action_execution_observed",
 "pending_confusion_action_execution_observed",
 "confusion_self_hit_damage_observed",
 "doubles_active_topology_observed",
 "selected_action_targeting_observed",
 "mat_block_active_entry_eligibility_observed",
 "fake_out_active_entry_eligibility_observed",
 "supreme_overlord_initial_active_observed",
})
_KINDS.update(STATUS_ACTION_DERIVED_KINDS)
_KINDS.update(CONFUSION_ACTION_DERIVED_KINDS)
_KINDS.update(CONFUSION_SELF_HIT_DAMAGE_DERIVED_KINDS)
_KINDS.update({
 "switch_entry_hp_transition_derived", "switch_entry_condition_applied_derived",
 "switch_entry_stat_stage_transition_derived", "switch_entry_weather_transition_derived",
 "switch_entry_hazard_transition_derived", "switch_entry_faint_derived",
 "switch_entry_ability_transition_derived",
})
class ObservationCollection:
 def __init__(self,session_id): self._session_id=session_id; self._items={}
 def add_confirmation_result(self,result):
  batch=self.add_confirmation_results((result,))
  return {"status":batch["status"]} if batch.get("status")!="added" else {"status":batch["results"][0]}
 def add_confirmation_results(self,results):
  if not isinstance(results,(tuple,list)) or not results:return {"status":"ignored","results":()}
  staged=deepcopy(self._items);out=[]
  for result in results:
   parsed=_confirmation_item(result,self._session_id)
   if isinstance(parsed,str):return {"status":parsed,"results":()}
   oid,item=parsed;old=staged.get(oid)
   if old is not None:
    if old!=item:return {"status":"conflicting_confirmation","results":()}
    out.append("duplicate");continue
   staged[oid]=item;out.append("added")
  self._items=staged
  return {"status":"added" if "added" in out else "duplicate","results":tuple(out)}
 def snapshot(self,session_id=None):
  if session_id is not None and session_id!=self._session_id:return {"status":"session_mismatch","session_id":self._session_id,"ordered_observations":[]}
  return {"status":"ready","session_id":self._session_id,"ordered_observations":deepcopy(sorted(self._items.values(),key=lambda x:(x["observation_sequence"],x["observation_id"]))),"limitations":["structured_only","no_store_or_reducer_application","no_provider_calls"]}
 def start_new_session(self,session_id): self._session_id=session_id;self._items={};return self.snapshot()

def _confirmation_item(result,session_id):
 if not isinstance(result,dict) or result.get("status")!="confirmed" or not isinstance(result.get("observation"),dict):return "ignored"
 item=deepcopy(result["observation"]);oid,seq=item.get("observation_id"),item.get("observation_sequence")
 if item.get("session_id")!=session_id:return "stale_session"
 turn=item.get("turn_number")
 if not isinstance(oid,str) or not oid or not isinstance(seq,int) or isinstance(seq,bool) or seq<1 or not _valid_turn_number(turn) or item.get("event_kind") not in _KINDS:return "invalid_observation"
 if item.get("event_kind") in DERIVED_KINDS and (item.get("trust")!=MECHANICS_DERIVED_TRUST or item.get("source")!=SWITCH_ENTRY_MECHANICS_SOURCE or item.get("scope")!="switch_entry" or not isinstance(item.get("payload",{}).get("source_switch_observation_id"),str)):return "invalid_observation"
 if item.get("event_kind") in STATUS_ACTION_DERIVED_KINDS and (item.get("trust")!=STATUS_ACTION_TRUST or item.get("source")!=CHAMPIONS_STATUS_ACTION_LIFECYCLE_SOURCE or item.get("scope")!="champions_status_action_lifecycle" or not isinstance(item.get("payload",{}).get("source_pending_observation_id"),str)):return "invalid_observation"
 if item.get("event_kind") in CONFUSION_ACTION_DERIVED_KINDS and (item.get("trust")!=CONFUSION_ACTION_TRUST or item.get("source")!=CHAMPIONS_CONFUSION_ACTION_LIFECYCLE_SOURCE or item.get("scope")!="champions_confusion_action_lifecycle" or not isinstance(item.get("payload",{}).get("source_pending_observation_id"),str)):return "invalid_observation"
 if item.get("event_kind") in CONFUSION_SELF_HIT_DAMAGE_DERIVED_KINDS and (item.get("trust")!=CONFUSION_SELF_HIT_DAMAGE_DERIVED_TRUST or item.get("source")!=CONFUSION_SELF_HIT_DAMAGE_DERIVED_SOURCE or item.get("scope")!="confusion_self_hit_damage_lifecycle" or not isinstance(item.get("payload",{}).get("source_damage_observation_id"),str)):return "invalid_observation"
 return oid,item

def _valid_turn_number(value): return value is None or (isinstance(value,int) and not isinstance(value,bool) and value>0)
