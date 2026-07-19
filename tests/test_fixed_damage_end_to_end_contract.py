from llm import advisor_client as client


def test_fixed_damage_acknowledgement_is_exact_and_mutation_safe():
    payload = {"deterministic_calculation_context": {"fixed_damage_assessment": {"move": "seismic-toss", "rule": "attacker-level", "damage": 50, "ko_status": "no_ko", "status": "resolved", "scope": "explicit-fixed-damage-rules-only"}}}
    expected = client.build_deterministic_result_acknowledgement_entries(payload)
    response = "[Trusted Context]\n[Deterministic Results]\n- Fixed damage | self | opponent | seismic-toss | attacker-level | 50 HP | explicit-fixed-damage-rules-only\n- Fixed-damage KO assessment | self | opponent | seismic-toss | no-ko\n[Advice]\nThe fixed rule is limited."
    assert client.validate_deterministic_result_acknowledgement(response, expected) is None
    assert client.validate_deterministic_result_acknowledgement(response.replace("50 HP", "51 HP"), expected) is not None


def test_fixed_damage_gate_off_omits_result():
    battle = {"moves": {"my_selected_move": {"move_id": "dragon-rage"}}}
    assert "fixed_damage_assessment" not in client._build_ui_selected_prompt(battle, enable_battle_state_context=False)
