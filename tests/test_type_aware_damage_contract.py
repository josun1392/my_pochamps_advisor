from llm.advisor_battle_state_context import build_deterministic_calculation_context


def test_missing_type_keeps_base_result_separate_and_marks_type_result_unavailable() -> None:
    context = build_deterministic_calculation_context(
        {"current_final_stats": [
            {"side": "self", "stat": "attack", "value": 200, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
            {"side": "opponent", "stat": "defense", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
        ]}, None, {"move_id": "tackle", "category": "physical", "power": 80}, None,
        {"my_active": {"types": ["normal"]}, "opponent_active": {"types": ["normal"]}},
    )
    assert context["base_damage_estimates"][0]["calculation_scope"] == "base_damage_stage_only"
    assert context["type_aware_damage_estimates"][0]["reason"] == "missing_move_type"
    assert context["damage_estimates"][0]["calculation_scope"] == "base_damage_stage_only"
