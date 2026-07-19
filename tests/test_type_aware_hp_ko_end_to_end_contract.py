from llm.advisor_battle_state_context import build_deterministic_calculation_context
from llm.advisor_client import build_deterministic_result_acknowledgement_entries


def test_type_aware_rolls_drive_hp_assessment_and_result_acknowledgement() -> None:
    context = build_deterministic_calculation_context(
        {"current_final_stats": [
            {"side": "self", "stat": "special-attack", "value": 200, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
            {"side": "opponent", "stat": "special-defense", "value": 150, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"},
        ]}, None, {"move_id": "thunderbolt", "category": "special", "power": 90, "type": "electric"},
        {"current_hp": [{"side": "opponent", "current_hp": 300, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp", "confidence": "known"}]},
        {"my_active": {"types": ["electric"]}, "opponent_active": {"types": ["water", "flying"]}},
    )
    assessment = context["hp_assessments"][0]
    assert assessment["calculation_scope"] == "base_damage_stage_stab_type"
    assert assessment["ohko"]["total_rolls"] == 16
    entries = build_deterministic_result_acknowledgement_entries({"deterministic_calculation_context": context})
    assert ("stab", "self", "thunderbolt", "applied", "1.5") in entries
    assert ("type_effectiveness", "self", "opponent", "thunderbolt", "4x") in entries
