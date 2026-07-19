from llm.advisor_client import build_deterministic_result_acknowledgement_entries


def test_special_result_has_separate_acknowledgements():
    payload = {"deterministic_calculation_context": {"hp_based_special_damage_assessment": {"move": "final-gambit", "rule": "user-current-hp-damage-and-self-faint", "damage": 80, "opponent_resulting_hp": 20, "status": "resolved", "scope": "explicit-hp-based-special-damage-only"}}}
    entries = build_deterministic_result_acknowledgement_entries(payload)
    assert entries[-3:] == (("hp_special_damage", "self", "opponent", "final-gambit", "user-current-hp-damage-and-self-faint", "80 HP", "explicit-hp-based-special-damage-only"), ("target_resulting_hp", "opponent", "final-gambit", "20 HP"), ("self_faint", "self", "final-gambit", "guaranteed-self-faint"))
