from advisor.canonical_defensive_stat_override_damage_family import resolve_canonical_defensive_stat_override_damage_move
from tests.test_v15_direct_mechanics_slice_contract import _modifier_result
def test_catalog_is_special_noncontact_psyshock():
 e=resolve_canonical_defensive_stat_override_damage_move(move={"move_id":"psyshock"})["effect"]
 assert (e["category"],e["power"],e["contact"],e["defensive_stat_name"]) == ("special",80,False,"defense")
def test_psyshock_uses_target_defense_stage():
 low=_modifier_result(move_id="psyshock",category="special",move_type="psychic",power=80,stages=[("self","special-attack",0),("opponent","defense",-1)])
 high=_modifier_result(move_id="psyshock",category="special",move_type="psychic",power=80,stages=[("self","special-attack",0),("opponent","defense",1)])
 assert low["defensive_stat_source"]["stat"]=="defense"
 assert max(low["exact_damage_rolls"])>max(high["exact_damage_rolls"])
