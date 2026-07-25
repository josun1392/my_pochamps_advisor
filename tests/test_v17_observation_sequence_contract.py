from llm.advisor_turn_snapshot import capture_ui_current_state_provenance, build_turn_snapshot_from_battle_input


def _battle(): return {"pokemon":{"my_active":{"name_en":"pikachu","slot_index":0},"opponent_active":{"name_en":"eevee","slot_index":1}},"moves":{"my_available_moves":[]}}
def _owner(side,pokemon,slot): return {"side":side,"pokemon_id":pokemon,"slot_index":slot,"session_id":"s","source":"ui_observed_damage_confirmation","trust":"user_confirmed_observation"}
def _event(oid,seq,amount=10,**extra):
    result={"event_kind":"direct_move_damage_observed","attacker":_owner("self","pikachu",0),"defender":_owner("opponent","eevee",1),"move_id":None,"move_slot":None,"damage_amount":amount,"hp_unit":"exact","source":"ui_observed_damage_confirmation","trust":"user_confirmed_observation","observed":True,"confirmed":True,"observation_id":oid,"observation_sequence":seq,"turn_number":None};result.update(extra);return result
def _capture(events): return capture_ui_current_state_provenance(_battle(),session_id="s",observed_damage_confirmations=events).get("observed_damage_context",{}).get("observed_damage_events",[])

def test_sequence_is_stable_monotonic_and_equal_damage_is_not_deduplicated():
    events=_capture([_event("b",2),_event("a",1),_event("c",3)])
    assert [(e["observation_id"],e["observation_sequence"],e["turn_number"]) for e in events]==[("a",1,None),("b",2,None),("c",3,None)]

def test_invalid_sequence_and_untrusted_turn_are_excluded_without_default_turn():
    assert _capture([_event("bad",0)])==[]
    assert _capture([_event("badturn",1,turn_number=1)])==[]
    trusted=_capture([_event("turn",1,turn_number=4,turn_source="ui_turn_number_confirmation",turn_trust="user_confirmed_observation")])[0]
    assert trusted["turn_number"]==4 and trusted["observation_sequence"]==1

def test_snapshot_is_detached_and_sequence_does_not_apply_state():
    raw=_event("one",1); captured=capture_ui_current_state_provenance(_battle(),session_id="s",observed_damage_confirmations=[raw]); frozen=build_turn_snapshot_from_battle_input(captured).to_dict(); raw["observation_sequence"]=9
    assert frozen["current_state"]["observed_damage_context"]["observed_damage_events"][0]["observation_sequence"]==1
    assert "current_hp_context" not in frozen["current_state"]
