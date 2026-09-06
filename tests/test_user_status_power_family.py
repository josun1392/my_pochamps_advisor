from advisor.canonical_user_status_power_family import resolve_canonical_user_status_power_move
from llm.advisor_battle_state_context import build_binary_condition_power_assessment
def _c(condition):return {"current_conditions":[{"side":"self","condition_type":condition}]}
def test_catalog_and_qualifying_conditions():
 e=resolve_canonical_user_status_power_move(move={"move_id":"facade"})["effect"]
 assert (e["category"],e["contact"],e["boosted_power"])==("physical",True,140)
def test_current_user_condition_only():
 assert build_binary_condition_power_assessment({"move_id":"facade"},_c("burn"),None)["effective_power"]==140
 assert build_binary_condition_power_assessment({"move_id":"facade"},_c("sleep"),None)["effective_power"]==70
 assert build_binary_condition_power_assessment({"move_id":"facade"},_c("freeze"),None)["effective_power"]==70
