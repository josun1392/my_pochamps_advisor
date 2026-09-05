from llm.advisor_detached_recent_damage_retaliation_attack_leaf import materialize_detached_recent_damage_retaliation_attack_leaves
from llm.advisor_detached_same_turn_last_incoming_attack_event import materialize_detached_same_turn_last_incoming_attack_event
from advisor.canonical_recent_damage_retaliation_family import resolve_canonical_recent_damage_retaliation_move


def _d0():
    a={"session_id":"s","side":"self","slot_index":0,"pokemon_id":"a"}; b={"session_id":"s","side":"opponent","slot_index":0,"pokemon_id":"b"}
    return {"session_id":"s","source_runtime_fingerprint":"r","strategy_preview_fingerprint":"p","decision_owner":a,"strategy_state":{"active":{"self":{"current_hp":80},"opponent":{"current_hp":100}}}},a,b

def test_catalog_binds_both_moves_and_rejects_unrelated_move():
    counter=resolve_canonical_recent_damage_retaliation_move(move={"move_id":"counter","priority":-5})
    mirror=resolve_canonical_recent_damage_retaliation_move(move={"move_id":"mirror-coat","priority":-5})
    assert counter["effect"]["qualifying_category"] == "physical" and counter["effect"]["multiplier"] == {"numerator":2,"denominator":1}
    assert mirror["effect"]["qualifying_category"] == "special" and mirror["effect"]["priority"] == -5
    assert resolve_canonical_recent_damage_retaliation_move(move={"move_id":"tackle"})["status"] == "unsupported"

def test_counter_uses_last_physical_hp_loss_and_zero_loss_is_one():
    d0,a,b=_d0(); event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"physical","qualifying_event":True,"hp_lost":30}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 60
    event["hp_lost"]=0
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 1

def test_mirror_coat_fails_closed_without_matching_event():
    d0,a,b=_d0()
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"mirror-coat","type":"psychic","category":"special","accuracy":100,"priority":-5,"contact":False},strict_hit_probability={"result":"always_hit"},incoming_event=None,applicability="applicable")
    leaf=out["terminal_leaves"][0]
    assert leaf["consequences"]["damage"] == 0
    assert leaf["consequences"]["recent_damage_retaliation"]["outcome"] == "failure_no_qualifying_recent_damage"

def test_type_immunity_keeps_valid_retaliation_at_zero_damage():
    d0,a,b=_d0(); event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"physical","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="immune")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 0

def test_category_mismatch_does_not_enable_retaliation():
    d0,a,b=_d0(); event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"physical","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"mirror-coat","type":"psychic","category":"special","accuracy":100,"priority":-5,"contact":False},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 0

def test_special_source_enables_mirror_coat():
    d0,a,b=_d0(); event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"special","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"mirror-coat","type":"psychic","category":"special","accuracy":100,"priority":-5,"contact":False},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 80

def test_retaliation_preserves_raw_damage_but_clamps_target_loss():
    d0,a,b=_d0(); d0["strategy_state"]["active"]["opponent"]["current_hp"]=30
    event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"physical","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    payload=out["terminal_leaves"][0]["consequences"]["recent_damage_retaliation"]
    assert payload["raw_damage"] == 80 and payload["actual_target_hp_loss"] == 30 and payload["target_post_hp"] == 0

def test_fainted_source_attacker_fails_closed_as_retaliation_target():
    d0,a,b=_d0(); d0["strategy_state"]["active"]["opponent"]["current_hp"]=0
    event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"physical","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 0

def test_foreign_source_attacker_cannot_be_silently_retargeted():
    d0,a,b=_d0(); foreign={**b,"pokemon_id":"other"}
    event={"status":"resolved","recipient":a,"source_attacker":foreign,"source_category":"physical","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="applicable")
    assert out["terminal_leaves"][0]["consequences"]["damage"] == 0

def test_protection_block_is_distinct_from_no_source_and_not_contact():
    d0,a,b=_d0(); event={"status":"resolved","recipient":a,"source_attacker":b,"source_category":"physical","qualifying_event":True,"hp_lost":40}
    out=materialize_detached_recent_damage_retaliation_attack_leaves(strategy_d0=d0,attacker=a,target=b,move={"move_id":"counter","type":"fighting","category":"physical","accuracy":100,"priority":-5,"contact":True},strict_hit_probability={"result":"always_hit"},incoming_event=event,applicability="blocked")
    leaf=out["terminal_leaves"][0]
    assert leaf["consequences"]["damage"] == 0 and leaf["consequences"]["contact"] == "not_applicable"
    assert leaf["consequences"]["recent_damage_retaliation"]["outcome"] == "blocked"

def test_event_uses_last_direct_multi_hit_strike_not_sum():
    d0,a,b=_d0()
    leaf={"action_type":"attack","leaf_id":"x","candidate_id":"attack:x","hit_state":"hit","ordered_hits":({"hit_index":1,"pre_hp":80,"post_hp":70,"target_routing":"target"},{"hit_index":2,"pre_hp":70,"post_hp":58,"target_routing":"target"}),"consequences":{"target_final_hp":58},"provenance":{"target":a,"attacker":b,"move_id":"x"}}
    event=materialize_detached_same_turn_last_incoming_attack_event(strategy_d0=d0,terminal_leaf=leaf,recipient=a,source_move_metadata={"category":"physical"})
    assert event["status"] == "resolved" and event["hp_lost"] == 12 and event["source_hit_path"]["hit_index"] == 2

def test_event_fails_closed_for_miss_or_substitute_route():
    d0,a,b=_d0(); base={"action_type":"attack","leaf_id":"x","candidate_id":"attack:x","consequences":{"target_final_hp":80,"source_hit_context":{"damage_route":"substitute"}},"provenance":{"target":a,"attacker":b,"move_id":"x"}}
    miss={**base,"hit_state":"miss"}
    sub={**base,"hit_state":"hit"}
    assert materialize_detached_same_turn_last_incoming_attack_event(strategy_d0=d0,terminal_leaf=miss,recipient=a,source_move_metadata={"category":"physical"})["status"] != "resolved"
    assert materialize_detached_same_turn_last_incoming_attack_event(strategy_d0=d0,terminal_leaf=sub,recipient=a,source_move_metadata={"category":"physical"})["status"] != "resolved"
