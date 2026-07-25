from llm.advisor_turn_snapshot import capture_ui_current_state_provenance, build_turn_snapshot_from_battle_input
def _battle(): return {"pokemon":{"my_active":{"name_en":"pikachu","slot_index":0},"opponent_active":{"name_en":"eevee","slot_index":1}}}
def _capture(records): return capture_ui_current_state_provenance(_battle(),session_id="s",switch_faint_confirmations=records).get("switch_faint_observation_context",{}).get("observations",[])
def _switch(**x):
 d={"event_kind":"pokemon_switch_observed","observation_id":"sw","observation_sequence":2,"turn_number":None,"session_id":"s","side":"self","switch_out_slot_index":1,"switch_out_pokemon_id":"raichu","switch_in_slot_index":0,"switch_in_pokemon_id":"pikachu","source":"ui_switch_confirmation","trust":"user_confirmed_observation","observed":True,"confirmed":True};d.update(x);return d
def _faint(**x):
 d={"event_kind":"pokemon_faint_observed","observation_id":"f","observation_sequence":1,"turn_number":None,"session_id":"s","side":"opponent","slot_index":1,"pokemon_id":"eevee","source":"ui_faint_confirmation","trust":"user_confirmed_observation","observed":True,"confirmed":True};d.update(x);return d
def test_switch_faint_are_explicit_ordered_and_detached():
 records=_capture([_switch(),_faint()]); assert [x["event_kind"] for x in records]==["pokemon_faint_observed","pokemon_switch_observed"]
 frozen=build_turn_snapshot_from_battle_input(capture_ui_current_state_provenance(_battle(),session_id="s",switch_faint_confirmations=[_switch()])).to_dict(); assert frozen["current_state"]["switch_faint_observation_context"]["observations"][0]["switch_in_pokemon_id"]=="pikachu"
def test_selection_hp_zero_and_invalid_switch_do_not_promote():
 assert _capture([])==[]
 assert _capture([_switch(switch_out_pokemon_id="pikachu")])==[]
 assert _capture([_faint(session_id="old")])==[]
