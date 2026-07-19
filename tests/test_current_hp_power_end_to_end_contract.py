from llm.advisor_client import build_deterministic_result_acknowledgement_entries, evaluate_deterministic_result_response
def test_power_acknowledgement_exact_and_semantic_boundary():
 payload={"deterministic_calculation_context":{"current_hp_based_power_assessment":{"move":"eruption","rule":"current-hp-proportional-150","effective_power":75,"status":"resolved","scope":"explicit-current-hp-based-move-power-only"}}}
 entries=build_deterministic_result_acknowledgement_entries(payload)
 response="""[Trusted Context]
[Deterministic Results]
- Current-HP move power | self | eruption | 75 | current-hp-proportional-150 | explicit-current-hp-based-move-power-only
[Advice]
At half HP, Eruption has power 75."""
 assert evaluate_deterministic_result_response(response,(),entries) is None
 assert evaluate_deterministic_result_response(response.replace("75 |","76 |"),(),entries)=="deterministic-results entry mismatch"
