from llm.advisor_client import build_deterministic_result_acknowledgement_entries
def test_speed_power_acknowledgement():
 p={"deterministic_calculation_context":{"speed_based_power_assessment":{"move":"electro-ball","rule":"self-to-opponent-speed-ratio","effective_power":120,"status":"resolved","scope":"explicit-speed-based-move-power-only"}}}
 assert build_deterministic_result_acknowledgement_entries(p)==(("speed_move_power","self","electro-ball","120","self-to-opponent-speed-ratio","explicit-speed-based-move-power-only"),)
