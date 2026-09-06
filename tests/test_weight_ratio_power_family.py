from advisor.canonical_weight_ratio_power_family import resolve_canonical_weight_ratio_power_move
from llm.advisor_battle_state_context import build_weight_based_power_assessment
def _p(weight):return build_weight_based_power_assessment({"move_id":"heavy-slam"},{"self_weight":weight,"opponent_weight":100})["effective_power"]
def test_catalog_and_exact_cross_multiplication():
 assert resolve_canonical_weight_ratio_power_move(move={"move_id":"heavy-slam"})["effect"]["contact"] is True
 assert resolve_canonical_weight_ratio_power_move(move={"move_id":"heat-crash"})["effect"]["type"]=="fire"
 assert [_p(x) for x in (199,200,299,300,399,400,499,500,501)]==[40,60,60,80,80,100,100,120,120]
 assert build_weight_based_power_assessment({"move_id":"heat-crash"},{"opponent_weight":100})["status"]=="unavailable"
