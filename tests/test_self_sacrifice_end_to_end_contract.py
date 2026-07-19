from llm.advisor_client import build_deterministic_result_acknowledgement_entries, evaluate_deterministic_result_response


def test_acknowledges_self_sacrifice_exactly_and_rejects_mutation():
    payload = {"deterministic_calculation_context": {"self_consequence_assessment": {"move": "explosion", "effect": "guaranteed_self_faint", "self_resulting_hp": 0, "self_faint_status": "guaranteed_self_faint", "status": "resolved", "scope": "explicit-self-sacrifice-and-hp-cost-only"}}}
    entries = build_deterministic_result_acknowledgement_entries(payload)
    response = """[Trusted Context]
[Deterministic Results]
- Self consequence | self | explosion | guaranteed-self-faint | 0 HP | explicit-self-sacrifice-and-hp-cost-only
[Advice]
Explosion causes the user to faint."""
    assert evaluate_deterministic_result_response(response, (), entries) is None
    assert evaluate_deterministic_result_response(response.replace("0 HP", "1 HP"), (), entries) == "deterministic-results malformed entry"


def test_self_damage_lines_and_follow_up_claim_rejection():
    payload = {"deterministic_calculation_context": {"self_consequence_assessment": {"move": "steel-beam", "effect": "maximum-hp-proportional-self-damage", "self_damage": 80, "self_resulting_hp": 0, "self_faint_status": "guaranteed_self_faint", "status": "resolved", "scope": "explicit-self-sacrifice-and-hp-cost-only"}}}
    entries = build_deterministic_result_acknowledgement_entries(payload)
    response = """[Trusted Context]
[Deterministic Results]
- Self damage | self | steel-beam | 80 HP | maximum-hp-proportional | explicit-self-sacrifice-and-hp-cost-only
- Self resulting HP | self | steel-beam | 0 HP
- Self-faint consequence | self | steel-beam | guaranteed-self-faint
[Advice]
The HP cost causes the user to faint."""
    assert evaluate_deterministic_result_response(response, (), entries) is None
    assert evaluate_deterministic_result_response(response.replace("[Advice]\n", "[Advice]\nThe next Pokemon automatically switches. "), (), entries) == "deterministic-results semantic boundary violation"
