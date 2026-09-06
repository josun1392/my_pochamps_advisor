from advisor.canonical_low_hp_bracket_power_family import resolve_canonical_low_hp_bracket_power_move
from llm.advisor_direct_mechanics import _current_hp_bracket_power_context
def _power(hp):return _current_hp_bracket_power_context(move_id="flail",direct_attacker={"current_hp":hp,"max_hp":48})["effective_power"]
def test_catalog_and_exact_x_boundaries():
 assert resolve_canonical_low_hp_bracket_power_move(move={"move_id":"flail"})["effect"]["contact"] is True
 assert resolve_canonical_low_hp_bracket_power_move(move={"move_id":"reversal"})["effect"]["type"]=="fighting"
 assert resolve_canonical_low_hp_bracket_power_move(move={"move_id":"tackle"})["status"]=="unsupported"
 assert [_power(x) for x in (33,32,17,16,10,9,5,4,2,1)]==[20,40,40,80,80,100,100,150,150,200]
def test_missing_hp_remains_unknown():
 assert _current_hp_bracket_power_context(move_id="reversal",direct_attacker={"max_hp":100})["status"]=="insufficient_context"
 assert _current_hp_bracket_power_context(move_id="reversal",direct_attacker={"current_hp":20})["status"]=="insufficient_context"
