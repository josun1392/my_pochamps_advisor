from advisor.canonical_alternate_offensive_stat_damage_family import resolve_canonical_alternate_offensive_stat_damage_move
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result

def test_catalog_metadata_is_exact():
    assert resolve_canonical_alternate_offensive_stat_damage_move(move={"move_id":"body-press"})["effect"]["offensive_stat_name"] == "defense"
    assert resolve_canonical_alternate_offensive_stat_damage_move(move={"move_id":"foul-play"})["effect"] == {"move_id":"foul-play","type":"dark","category":"physical","power":95,"accuracy":100,"priority":0,"contact":True,"protection_blockable":True,"family":"alternate_offensive_stat","offensive_stat_owner":"target","offensive_stat_name":"attack"}

def test_body_press_uses_user_defense_stage_not_attack_stage():
    low = _modifier_result(move_id="body-press", move_type="fighting", power=80, stages=[("self","defense",-1),("opponent","defense",0)])
    high = _modifier_result(move_id="body-press", move_type="fighting", power=80, stages=[("self","defense",1),("opponent","defense",0)])
    assert low["offensive_stat_source"] == {"family":"alternate_offensive_stat","owner":"attacker","stat":"defense","stage_side":"self"}
    assert min(high["exact_damage_rolls"]) > min(low["exact_damage_rolls"])

def test_foul_play_uses_target_attack_stage_and_keeps_user_identity():
    low = _modifier_result(move_id="foul-play", move_type="dark", power=95, stages=[("opponent","attack",-1),("opponent","defense",0)])
    high = _modifier_result(move_id="foul-play", move_type="dark", power=95, stages=[("opponent","attack",1),("opponent","defense",0)])
    assert high["offensive_stat_source"] == {"family":"alternate_offensive_stat","owner":"defender","stat":"attack","stage_side":"opponent"}
    assert min(high["exact_damage_rolls"]) > min(low["exact_damage_rolls"])
