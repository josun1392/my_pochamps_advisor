from llm.advisor_candidate_contract import complete_recommendation_cycle, prepare_ui_recommendation_cycle


def test_sanitized_resolved_fixture_accepts_the_exact_selectable_move_slot_pair():
    def stat(side, name, value):
        return {"side": side, "stat": name, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}
    battle = {"scenario": {"mode": "advisor"}, "pokemon": {"my_active": {"name_en": "self"}, "opponent_active": {"name_en": "opponent"}}, "final_stat_context": {"current_final_stats": [stat("self", "attack", 200), stat("self", "special-attack", 200), stat("self", "speed", 200), stat("opponent", "defense", 150), stat("opponent", "special-defense", 150), stat("opponent", "speed", 100)]}}
    prepared = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "tackle"}, {"move_id": "hyper-beam"}], battle_input=battle, move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}, "hyper-beam": {"category": "special", "power": 150, "type": "normal"}})
    response = {"recommendation_status": "resolved", "recommended_move": "hyper-beam", "recommended_slot_index": 1, "primary_reasons": [], "risks": [], "alternatives": []}
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=response)
    assert prepared["status"] == "ready"
    assert completed["status"] == "resolved" and completed["recommendation_result"]["recommended_move"] == "hyper-beam"
