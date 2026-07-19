from llm.advisor_battle_state_context import build_deterministic_calculation_context


def test_explicit_self_sacrifice_is_separate_from_drain_recoil_and_final_gambit():
    result = build_deterministic_calculation_context(None, selected_move={"move_id": "explosion"})
    assert "self_consequence_assessment" in result and "drain_recoil_assessment" not in result
    final_gambit = build_deterministic_calculation_context(None, selected_move={"move_id": "final-gambit"})
    assert "hp_based_special_damage_assessment" in final_gambit and "self_consequence_assessment" not in final_gambit


def test_memento_does_not_claim_stat_changes():
    result = build_deterministic_calculation_context(None, selected_move={"move_id": "memento"})["self_consequence_assessment"]
    assert set(result) == {"move", "scope", "effect", "self_resulting_hp", "self_faint_status", "status"}
