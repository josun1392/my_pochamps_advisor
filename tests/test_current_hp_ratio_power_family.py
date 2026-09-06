from advisor.canonical_current_hp_ratio_power_family import resolve_canonical_current_hp_ratio_power_move
from llm.advisor_direct_mechanics import _current_hp_proportional_power_context
def test_catalog_and_exact_execution_hp_arithmetic():
 assert resolve_canonical_current_hp_ratio_power_move(move={"move_id":"eruption"})["effect"]["contact"] is False
 assert resolve_canonical_current_hp_ratio_power_move(move={"move_id":"water-spout"})["effect"]["type"]=="water"
 assert resolve_canonical_current_hp_ratio_power_move(move={"move_id":"dragon-energy"})["status"]=="unsupported"
 assert _current_hp_proportional_power_context(move_id="eruption",direct_attacker={"current_hp":67,"max_hp":101})["effective_power"]==99
 one=_current_hp_proportional_power_context(move_id="water-spout",direct_attacker={"current_hp":1,"max_hp":300});assert one["effective_power"]==1
