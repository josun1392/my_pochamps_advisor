from advisor.canonical_target_status_power_family import resolve_canonical_target_status_power_move
from llm.advisor_battle_state_context import build_binary_condition_power_assessment
def _c(condition):return {"current_conditions":[{"side":"opponent","condition_type":condition}]}
def test_catalog_and_exact_existing_condition_rules():
 assert resolve_canonical_target_status_power_move(move={"move_id":"hex"})["effect"]["boosted_power"]==130
 assert resolve_canonical_target_status_power_move(move={"move_id":"venoshock"})["effect"]["qualifier"]=="poison_or_toxic"
 assert resolve_canonical_target_status_power_move(move={"move_id":"infernal-parade"})["status"]=="unsupported"
def test_hex_any_status_venoshock_only_poison():
 assert build_binary_condition_power_assessment({"move_id":"hex"},_c("burn"),None)["effective_power"]==130
 assert build_binary_condition_power_assessment({"move_id":"venoshock"},_c("burn"),None)["effective_power"]==65
 assert build_binary_condition_power_assessment({"move_id":"venoshock"},_c("toxic"),None)["effective_power"]==130
