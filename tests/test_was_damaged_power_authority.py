from llm.advisor_detached_was_damaged_by_target_power_authority import materialize_detached_was_damaged_by_target_power_authority

def _owners():
    return {"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"},{"session_id":"s","side":"opponent","slot_index":0,"pokemon_id":"b"}

def test_avalanche_revenge_use_120_only_for_positive_exact_target_damage():
    user,target=_owners()
    for move in ({"move_id":"avalanche","type":"ice","category":"physical","power":60,"accuracy":100,"priority":-4,"contact":True},{"move_id":"revenge","type":"fighting","category":"physical","power":60,"accuracy":100,"priority":-4,"contact":True}):
        event={"status":"resolved","recipient":user,"source_attacker":target,"qualifying_event":True,"hp_lost":1}
        assert materialize_detached_was_damaged_by_target_power_authority(move=move,user=user,target=target,incoming_event=event)["selected_base_power"] == 120
        event["hp_lost"]=0
        assert materialize_detached_was_damaged_by_target_power_authority(move=move,user=user,target=target,incoming_event=event)["selected_base_power"] == 60

def test_uses_any_positive_direct_strike_from_the_exact_source_leaf():
    user,target=_owners()
    move={"move_id":"avalanche","type":"ice","category":"physical","power":60,"accuracy":100,"priority":-4,"contact":True}
    event={"status":"resolved","recipient":user,"source_attacker":target,"qualifying_event":True,"hp_lost":0}
    leaf={"ordered_hits":[{"target_routing":"target","actual_damage":10},{"target_routing":"target","actual_damage":0}]}
    authority=materialize_detached_was_damaged_by_target_power_authority(move=move,user=user,target=target,incoming_event=event,source_terminal_leaf=leaf)
    assert authority["was_damaged_by_target"] is True
    assert authority["selected_base_power"] == 120
