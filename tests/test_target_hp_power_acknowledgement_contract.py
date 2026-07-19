from llm.advisor_client import build_deterministic_result_acknowledgement_entries
def test_resolved_acknowledgement():
 p={"deterministic_calculation_context":{"target_hp_based_power_assessment":{"move":"crush-grip","rule":"target-current-hp-proportional","effective_power":61,"status":"resolved","scope":"explicit-target-hp-based-move-power-only"}}}
 assert build_deterministic_result_acknowledgement_entries(p)[0][0]=="target_hp_move_power"
