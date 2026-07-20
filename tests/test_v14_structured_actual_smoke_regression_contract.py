import llm.advisor_client as client


def _stat(side, stat, value):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def test_sanitized_six_field_smoke_shape_preserves_evidence_when_completion_rejects_claim(monkeypatch):
    battle = {"scenario": {"mode": "advisor"}, "pokemon": {"my_active": {"name_en": "self"}, "opponent_active": {"name_en": "opponent"}}, "final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}
    response = {"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [{"kind": "partial_context", "claim": "missing evidence"}], "risks": [], "alternatives": []}
    usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "model": "sanitized", "tool": "structured_recommendation", "success": True, "failure_code": None}
    monkeypatch.setattr(client, "call_structured_recommendation_provider", lambda **_: (response, usage))
    result = client.run_structured_ui_recommendation(selected_moves=[{"move_id": "tackle"}], battle_input=battle, move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}}, model="sanitized")
    assert result["status"] == "response_validation_failed"
    assert result["prepared_cycle"]["evidence_bundle"] and result["presentation_model"]["recommended_move"] is None
    assert "response_payload" not in result and "raw_response" not in result
