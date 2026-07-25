from llm.advisor_turn_snapshot import capture_ui_current_state_provenance, build_turn_snapshot_from_battle_input

def battle(): return {"pokemon":{"my_active":{"name_en":"pikachu","slot_index":0},"opponent_active":{"name_en":"eevee","slot_index":1}}}
def event(kind, scope, oid, seq, **x):
 d={"event_kind":kind,"scope":scope,"observation_id":oid,"observation_sequence":seq,"session_id":"s","source":"ui_lifecycle_confirmation","trust":"user_confirmed_observation","observed":True,"confirmed":True,"payload":{}}; d.update(x); return d
def capture(values): return capture_ui_current_state_provenance(battle(),session_id="s",lifecycle_confirmations=values).get("lifecycle_observation_context",{}).get("observations",[])
def test_condition_item_ability_field_side_contracts_and_eligibility():
 values=[event("condition_applied_observed","pokemon","c",3,side="self",slot_index=0,pokemon_id="pikachu"),event("item_activation_observed","pokemon","i",2,side="self",slot_index=0,pokemon_id="pikachu"),event("ability_activation_observed","pokemon","a",1,side="opponent",slot_index=1,pokemon_id="eevee"),event("weather_started_observed","field","w",4),event("side_condition_ended_observed","side","x",5,side="self")]
 result=capture(values); assert [x["observation_id"] for x in result]==["a","i","c","w","x"]
 assert [x["reducer_eligibility"] for x in result]==["evidence_only","evidence_only","candidate","candidate","candidate"]
def test_current_state_hp_or_selection_never_creates_lifecycle_history_and_invalid_is_excluded():
 assert capture([])==[]
 assert capture([event("condition_removed_observed","pokemon","bad",1,side="self",slot_index=1,pokemon_id="pikachu"),event("terrain_ended_observed","field","old",2,session_id="old")])==[]
def test_duplicate_conflict_and_snapshot_are_detached_without_state_transition():
 first=event("weather_started_observed","field","same",2); conflict=event("weather_ended_observed","field","same",1)
 result=capture([first,conflict]); assert len(result)==1 and result[0]["event_kind"]=="weather_started_observed"
 frozen=build_turn_snapshot_from_battle_input(capture_ui_current_state_provenance(battle(),session_id="s",lifecycle_confirmations=[first])).to_dict(); first["observation_sequence"]=9
 assert frozen["current_state"]["lifecycle_observation_context"]["observations"][0]["observation_sequence"]==2
 assert "field_state_context" not in frozen["current_state"]
